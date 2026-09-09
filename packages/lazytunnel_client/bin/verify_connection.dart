/// Private acceptance input: {"profile":{...},"credentials":{...}}.
/// Emits counts and outcomes only, never credentials or endpoint identities.
import 'dart:convert';
import 'dart:io';
import 'package:lazytunnel_client/lazytunnel_client.dart';

Future<void> main(List<String> args) async {
  if (args.length != 1) {
    stderr.writeln('Usage: dart run bin/verify_connection.dart PRIVATE_JSON');
    exitCode = 2;
    return;
  }
  final data =
      jsonDecode(await File(args.single).readAsString())
          as Map<String, dynamic>;
  final p = ConnectionProfile.fromJson(
    Map<String, dynamic>.from(data['profile'] as Map),
  );
  final c = Credentials.fromJson(
    Map<String, dynamic>.from(data['credentials'] as Map),
  );
  final connection = await AgentConnection.connect(p, c);
  try {
    final snapshot = await connection.api.snapshot();
    stdout.writeln(
      'Authenticated agent: ${snapshot.devices.length} devices; ${snapshot.viewers.length} viewers',
    );
    if (connection.supportsTerminal && snapshot.devices.isNotEmpty) {
      final shell = await connection.terminal(snapshot.devices.first.name);
      final output = StringBuffer();
      final sub = shell.output.listen(output.write);
      final errors = shell.errors.listen((_) {});
      shell.write("printf 'LAZY_NATIVE_%s\\n' VERIFIED\r");
      for (
        var i = 0;
        i < 100 && !output.toString().contains('LAZY_NATIVE_VERIFIED');
        i++
      ) {
        await Future<void>.delayed(const Duration(milliseconds: 100));
      }
      if (!output.toString().contains('LAZY_NATIVE_VERIFIED'))
        throw StateError('SSH terminal did not echo the acceptance marker');
      shell.write('exit\r');
      shell.close();
      await sub.cancel();
      await errors.cancel();
      stdout.writeln('Native SSH terminal: verified');
    }
    if (snapshot.viewers.any((v) => v.available)) {
      final viewer = snapshot.viewers.firstWhere((v) => v.available);
      final uri = await connection.viewerUri(viewer);
      final http = HttpClient()..findProxy = (_) => 'DIRECT';
      try {
        final response = await (await http.getUrl(
          uri,
        )).close().timeout(const Duration(seconds: 10));
        await response.drain<void>();
        if (response.statusCode >= 500)
          throw StateError('Viewer returned an upstream error');
        stdout.writeln('Native viewer forwarding: HTTP ${response.statusCode}');
      } finally {
        http.close(force: true);
      }
    }
  } finally {
    await connection.close();
  }
  stdout.writeln('App-owned connections closed; agent remains independent');
}
