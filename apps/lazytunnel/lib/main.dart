import 'package:flutter/material.dart';
import 'app.dart';
import 'profile_store.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(LazyTunnelApp(store: SecureProfileStore()));
}
