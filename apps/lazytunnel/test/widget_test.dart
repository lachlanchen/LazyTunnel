import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lazytunnel_app/app.dart';
import 'package:lazytunnel_app/profile_store.dart';
import 'package:lazytunnel_app/connection_form.dart';

class MemoryStore implements ProfileStore {
  List<SavedConnection> items = [];
  @override
  Future<List<SavedConnection>> load() async => items;
  @override
  Future<void> save(List<SavedConnection> profiles) async {
    items = profiles;
  }
}

void main() {
  for (final size in [const Size(390, 844), const Size(1280, 850)]) {
    testWidgets('Native connection screen fits $size', (tester) async {
      tester.view.physicalSize = size;
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(
        LazyTunnelApp(store: MemoryStore(), discoverLocal: () async => null),
      );
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 100)),
      );
      await tester.pumpAndSettle();
      expect(find.text('LazyTunnel'), findsOneWidget);
      expect(find.text('Connect your workspace'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.tap(find.byTooltip('Light or dark theme'));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    });
  }
  testWidgets('Missing SSH fingerprint prevents connection', (tester) async {
    var attempts = 0;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: ConnectionForm(
              onConnect: (_, _) async {
                attempts++;
              },
            ),
          ),
        ),
      ),
    );
    await tester.enterText(find.byKey(const ValueKey('host')), 'example.test');
    await tester.enterText(find.byKey(const ValueKey('user')), 'example');
    await tester.ensureVisible(find.text('Connect'));
    await tester.tap(find.text('Connect'));
    await tester.pumpAndSettle();
    expect(attempts, 0);
    expect(find.text('Required'), findsWidgets);
  });
}
