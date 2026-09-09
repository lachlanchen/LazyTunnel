import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:dartssh2/dartssh2.dart';
import 'api.dart';
import 'models.dart';

class HostKeyMismatch implements Exception {
  final String host, expected, received;
  const HostKeyMismatch(this.host, this.expected, this.received);
  @override
  String toString() =>
      'Host identity did not match for $host. Expected $expected; received $received. '
      'Verify the fingerprint on that computer before changing the saved profile.';
}

/// Bounded local TCP endpoint. Closing it affects only this application's channels.
class LocalForward {
  final ServerSocket _server;
  final Set<Socket> _sockets = {};
  final Set<SSHForwardChannel> _channels = {};
  bool _closed = false;
  int get port => _server.port;
  LocalForward._(this._server, SSHClient client, int remotePort) {
    _server.listen((socket) async {
      if (_closed || _sockets.length >= 32) {
        socket.destroy();
        return;
      }
      _sockets.add(socket);
      SSHForwardChannel? channel;
      try {
        channel = await client
            .forwardLocal('127.0.0.1', remotePort)
            .timeout(const Duration(seconds: 10));
        if (_closed) {
          channel.close();
          socket.destroy();
          return;
        }
        _channels.add(channel);
        final active = channel;
        final inbound = socket.listen(
          active.sink.add,
          onError: (_) => active.close(),
          onDone: active.close,
        );
        try {
          await socket.addStream(active.stream);
        } finally {
          await inbound.cancel();
        }
      } catch (_) {
        // A closed browser tab or unavailable viewer is local to this channel.
      } finally {
        socket.destroy();
        _sockets.remove(socket);
        channel?.close();
        _channels.remove(channel);
      }
    });
  }
  static Future<LocalForward> open(SSHClient client, int remotePort) async =>
      LocalForward._(
        await ServerSocket.bind(InternetAddress.loopbackIPv4, 0),
        client,
        remotePort,
      );
  Future<void> close() async {
    if (_closed) return;
    _closed = true;
    await _server.close();
    for (final socket in _sockets.toList()) {
      socket.destroy();
    }
    for (final channel in _channels.toList()) {
      channel.close();
    }
  }
}

class AgentConnection {
  final ConnectionProfile profile;
  final AgentApi api;
  final SSHClient? _ssh, _jump;
  final List<LocalForward> _forwards;
  final Map<int, LocalForward> _viewers = {};
  bool _closed = false;
  AgentConnection._(
    this.profile,
    this.api,
    this._ssh,
    this._jump,
    this._forwards,
  );
  bool get supportsTerminal => _ssh != null;

  static Future<SSHClient> _authenticate(
    SSHSocket socket,
    ConnectionProfile profile,
    Credentials credentials,
  ) async {
    HostKeyMismatch? mismatch;
    final client = SSHClient(
      socket,
      username: profile.username,
      identities: credentials.privateKey.isEmpty
          ? null
          : SSHKeyPair.fromPem(
              credentials.privateKey,
              credentials.passphrase.isEmpty ? null : credentials.passphrase,
            ),
      onPasswordRequest: () =>
          credentials.password.isEmpty ? null : credentials.password,
      onVerifyHostKey: (type, fingerprint) {
        final actual = utf8.decode(fingerprint);
        if (actual != profile.fingerprint) {
          mismatch = HostKeyMismatch(profile.host, profile.fingerprint, actual);
          return false;
        }
        return true;
      },
      keepAliveInterval: const Duration(seconds: 20),
    );
    try {
      await client.authenticated.timeout(const Duration(seconds: 20));
      return client;
    } catch (_) {
      client.close();
      if (mismatch != null) throw mismatch!;
      rethrow;
    }
  }

  static Future<AgentConnection> connect(
    ConnectionProfile profile,
    Credentials credentials,
  ) async {
    profile.validate();
    if (credentials.accessCode.trim().isEmpty)
      throw const AgentException('Enter the agent access code.');
    SSHClient? ssh, jump;
    LocalForward? forward;
    AgentApi? api;
    try {
      int port = profile.agentPort;
      if (!profile.local) {
        SSHSocket socket;
        if (profile.jump != null) {
          if (credentials.jump == null)
            throw ArgumentError('Jump host credentials are required.');
          final jp = profile.jump!;
          jump = await _authenticate(
            await SSHSocket.connect(
              jp.host,
              jp.sshPort,
              timeout: const Duration(seconds: 10),
            ),
            jp,
            credentials.jump!,
          );
          socket = await jump.forwardLocal(profile.host, profile.sshPort);
        } else {
          socket = await SSHSocket.connect(
            profile.host,
            profile.sshPort,
            timeout: const Duration(seconds: 10),
          );
        }
        ssh = await _authenticate(socket, profile, credentials);
        forward = await LocalForward.open(ssh, profile.agentPort);
        port = forward.port;
      }
      api = AgentApi(
        uri: Uri.parse('http://127.0.0.1:$port'),
        agentPort: profile.agentPort,
        accessCode: credentials.accessCode.trim(),
      );
      await api.snapshot();
      return AgentConnection._(profile, api, ssh, jump, [
        if (forward != null) forward,
      ]);
    } catch (_) {
      api?.close();
      await forward?.close();
      ssh?.close();
      jump?.close();
      rethrow;
    }
  }

  Future<Uri> viewerUri(Viewer viewer) async {
    if (_closed)
      throw const AgentException('Reconnect before opening a viewer.');
    if (!viewer.available)
      throw const AgentException('Start this forward before opening it.');
    if (viewer.localPort < 1024 ||
        viewer.localPort > 65535 ||
        !viewer.path.startsWith('/') ||
        viewer.path.startsWith('//') ||
        viewer.path.contains('\\'))
      throw const AgentException('Invalid viewer address.');
    var port = viewer.localPort;
    if (_ssh != null) {
      _viewers[port] ??= await LocalForward.open(_ssh, port);
      port = _viewers[port]!.port;
    }
    return Uri.parse('http://127.0.0.1:$port${viewer.path}');
  }

  /// Start a PTY on the controller, then use its existing restricted fleet config.
  Future<ShellSession> terminal(
    String device, {
    int width = 80,
    int height = 24,
  }) async {
    if (_ssh == null || _closed)
      throw const AgentException(
        'Connect through SSH to use the in-app terminal.',
      );
    if (!RegExp(r'^[a-z0-9][a-z0-9-]{0,19}$').hasMatch(device))
      throw ArgumentError('Invalid enrolled device.');
    final session = await _ssh.execute(
      'exec ssh -F "\$HOME/.config/lazytunnel-fleet/ssh_config" '
      '-o StrictHostKeyChecking=yes -o ForwardAgent=no -o ForwardX11=no -t lazy-$device',
      pty: SSHPtyConfig(width: width, height: height),
    );
    return ShellSession(session);
  }

  Future<void> close() async {
    if (_closed) return;
    _closed = true;
    api.close();
    for (final f in [..._forwards, ..._viewers.values]) {
      await f.close();
    }
    _ssh?.close();
    _jump?.close();
  }
}

/// Terminal streams and dimensions without any dependency on a widget toolkit.
class ShellSession {
  final SSHSession _session;
  ShellSession(this._session);
  Stream<String> get output => _session.stdout.cast<List<int>>().transform(
    const Utf8Decoder(allowMalformed: true),
  );
  Stream<String> get errors => _session.stderr.cast<List<int>>().transform(
    const Utf8Decoder(allowMalformed: true),
  );
  Future<void> get done => _session.done;
  void write(String text) => _session.stdin.add(utf8.encode(text));
  void resize(int columns, int rows, int pixelWidth, int pixelHeight) =>
      _session.resizeTerminal(columns, rows, pixelWidth, pixelHeight);
  void close() => _session.close();
}
