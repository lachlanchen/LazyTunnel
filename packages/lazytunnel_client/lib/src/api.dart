import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'models.dart';

class AgentException implements Exception {
  final String message;
  final int? status;
  const AgentException(this.message, [this.status]);
  @override
  String toString() => message;
}

/// Loopback HTTP only; [uri] may be the local end of a verified SSH tunnel.
class AgentApi {
  final Uri uri;
  final int agentPort;
  final String accessCode;
  final HttpClient _http = HttpClient()
    ..connectionTimeout = const Duration(seconds: 8);
  AgentApi({
    required this.uri,
    required this.agentPort,
    required this.accessCode,
  }) {
    if (uri.scheme != 'http' ||
        !['localhost', '127.0.0.1'].contains(uri.host) ||
        uri.userInfo.isNotEmpty ||
        uri.hasQuery ||
        uri.hasFragment) {
      throw ArgumentError('Agent API must use a local loopback transport.');
    }
    _http.findProxy = (_) => 'DIRECT';
  }
  Future<Map<String, dynamic>> _call(
    String path, [
    Map<String, dynamic>? data,
  ]) async {
    try {
      final request = await _http.openUrl(
        data == null ? 'GET' : 'POST',
        uri.resolve(path),
      );
      request.followRedirects = false;
      request.headers.set(HttpHeaders.hostHeader, '127.0.0.1:$agentPort');
      request.headers.set(
        HttpHeaders.authorizationHeader,
        'Bearer $accessCode',
      );
      if (data != null) {
        final bytes = utf8.encode(jsonEncode(data));
        if (bytes.length > 8192)
          throw const AgentException('Request is too large.');
        request.headers.contentType = ContentType.json;
        request.contentLength = bytes.length;
        request.add(bytes);
      }
      final response = await request.close().timeout(
        const Duration(seconds: 30),
      );
      final bytes = <int>[];
      await for (final chunk in response.timeout(const Duration(seconds: 10))) {
        if (bytes.length + chunk.length > 2 * 1024 * 1024) {
          throw const AgentException('Agent response exceeded the size limit.');
        }
        bytes.addAll(chunk);
      }
      final result = jsonDecode(utf8.decode(bytes)) as Map<String, dynamic>;
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw AgentException(
          result['error'] as String? ?? 'Agent request failed.',
          response.statusCode,
        );
      }
      return result;
    } on AgentException {
      rethrow;
    } on TimeoutException {
      throw const AgentException(
        'Agent timed out. Existing remote services were preserved.',
      );
    } on SocketException {
      throw const AgentException(
        'Cannot reach the agent. Check the connection and try again.',
      );
    } on FormatException {
      throw const AgentException(
        'The endpoint did not return a valid agent response.',
      );
    }
  }

  Future<Snapshot> snapshot() async =>
      Snapshot.fromJson(await _call('/api/state'));
  Future<void> check([String? device]) async {
    await _call('/api/check', {if (device != null) 'device': device});
  }

  Future<void> saveViewer({
    required String name,
    required String device,
    required int remotePort,
    required int localPort,
    required String path,
    required String mode,
  }) async {
    await _call('/api/viewers', {
      'name': name,
      'device': device,
      'remote_port': remotePort,
      'local_port': localPort,
      'path': path,
      'mode': mode,
    });
  }

  Future<void> action(String id, String action) async {
    await _call('/api/viewers/action', {'id': id, 'action': action});
  }

  void close() => _http.close(force: true);
}
