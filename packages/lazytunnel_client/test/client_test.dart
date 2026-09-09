import 'dart:convert';
import 'dart:io';
import 'package:lazytunnel_client/lazytunnel_client.dart';
import 'package:test/test.dart';

void main() {
  test('Plain HTTP cannot leak credentials to a remote address', () {
    expect(
      () => AgentApi(
        uri: Uri.parse('http://example.test:17766'),
        agentPort: 17766,
        accessCode: 'secret',
      ),
      throwsArgumentError,
    );
    expect(
      () => const ConnectionProfile(local: true, host: '10.1.2.3').validate(),
      throwsArgumentError,
    );
  });
  test('SSH requires a pinned fingerprint and one bounded jump', () {
    expect(
      () => const ConnectionProfile(
        host: 'example.test',
        username: 'user',
      ).validate(),
      throwsArgumentError,
    );
    const valid = ConnectionProfile(
      host: 'example.test',
      username: 'user',
      fingerprint: 'SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
    );
    valid.validate();
    expect(
      ConnectionProfile.fromJson(valid.toJson()).fingerprint,
      valid.fingerprint,
    );
    expect(
      () => ConnectionProfile(
        host: valid.host,
        username: valid.username,
        fingerprint: valid.fingerprint,
        jump: ConnectionProfile(
          host: valid.host,
          username: valid.username,
          fingerprint: valid.fingerprint,
          jump: valid,
        ),
      ).validate(),
      throwsArgumentError,
    );
    expect(valid.toJson().keys, isNot(contains('password')));
  });
  test('Model parsing preserves Unicode names and unchecked state', () {
    final snapshot = Snapshot.fromJson({
      'version': 1,
      'devices': [
        {
          'name': 'example',
          'user': 'user',
          'aliases': ['example'],
          'local': true,
        },
      ],
      'viewers': [
        {
          'id': 'abc',
          'name': '中文 / 日本語',
          'device': 'example',
          'mode': 'local',
          'status': 'existing',
          'path': '/vnc.html',
          'local_port': 6080,
          'remote_port': 6080,
        },
      ],
      'checking': false,
      'managed_forwards': true,
    });
    expect(snapshot.devices.single.status, 'unchecked');
    expect(snapshot.viewers.single.name, '中文 / 日本語');
    expect(snapshot.viewers.single.available, isTrue);
  });
  group('Agent transport', () {
    late HttpServer server;
    late AgentApi api;
    setUp(() async {
      server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      api = AgentApi(
        uri: Uri.parse('http://127.0.0.1:${server.port}'),
        agentPort: 17766,
        accessCode: 'private-test-token',
      );
    });
    tearDown(() async {
      api.close();
      await server.close(force: true);
    });
    test(
      'Tunnel preserves agent Host and bearer auth without origin or URL secrets',
      () async {
        server.listen((request) async {
          expect(request.headers.value('host'), '127.0.0.1:17766');
          expect(
            request.headers.value('authorization'),
            'Bearer private-test-token',
          );
          expect(request.uri.query, isEmpty);
          request.response.headers.contentType = ContentType.json;
          request.response.write(
            jsonEncode({'devices': [], 'viewers': [], 'checking': false}),
          );
          await request.response.close();
        });
        expect((await api.snapshot()).devices, isEmpty);
      },
    );
    test('Rejected authentication is not retried or hidden', () async {
      var requests = 0;
      server.listen((request) async {
        requests++;
        request.response.statusCode = 401;
        request.response.write('{"error":"Invalid code"}');
        await request.response.close();
      });
      await expectLater(
        api.snapshot(),
        throwsA(isA<AgentException>().having((e) => e.status, 'status', 401)),
      );
      expect(requests, 1);
    });
    test('Redirect never carries bearer token to another endpoint', () async {
      var requests = 0;
      server.listen((request) async {
        requests++;
        request.response.statusCode = 302;
        request.response.headers.set(
          'Location',
          'http://127.0.0.1:${server.port}/stolen',
        );
        request.response.write('{"error":"Redirect refused"}');
        await request.response.close();
      });
      await expectLater(api.snapshot(), throwsA(isA<AgentException>()));
      expect(requests, 1);
    });
    test('Write body contains only the explicit viewer action', () async {
      server.listen((request) async {
        expect(request.method, 'POST');
        expect(request.uri.path, '/api/viewers/action');
        expect(jsonDecode(await utf8.decoder.bind(request).join()), {
          'id': 'abc',
          'action': 'start',
        });
        request.response.write('{"ok":true}');
        await request.response.close();
      });
      await api.action('abc', 'start');
    });
  });
}
