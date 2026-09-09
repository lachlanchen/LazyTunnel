import 'dart:io';
import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:lazytunnel_client/lazytunnel_client.dart';

class SavedConnection {
  final ConnectionProfile profile;
  final Credentials credentials;
  const SavedConnection(this.profile, this.credentials);
  Map<String, dynamic> toJson() => {
    'profile': profile.toJson(),
    'credentials': credentials.toJson(),
  };
  factory SavedConnection.fromJson(Map<String, dynamic> j) => SavedConnection(
    ConnectionProfile.fromJson(Map<String, dynamic>.from(j['profile'] as Map)),
    Credentials.fromJson(Map<String, dynamic>.from(j['credentials'] as Map)),
  );
}

abstract interface class ProfileStore {
  Future<List<SavedConnection>> load();
  Future<void> save(List<SavedConnection> profiles);
}

/// All persisted fields live in the platform secret store, never a plain JSON file.
class SecureProfileStore implements ProfileStore {
  final FlutterSecureStorage storage;
  SecureProfileStore({this.storage = const FlutterSecureStorage()});
  static const key = 'lazytunnel.connections.v1';
  @override
  Future<List<SavedConnection>> load() async {
    final value = await storage.read(key: key);
    if (value == null) return [];
    return (jsonDecode(value) as List)
        .map(
          (j) => SavedConnection.fromJson(Map<String, dynamic>.from(j as Map)),
        )
        .toList();
  }

  @override
  Future<void> save(List<SavedConnection> profiles) => storage.write(
    key: key,
    value: jsonEncode(profiles.map((p) => p.toJson()).toList()),
  );
}

/// Local convenience only. No token is logged, exported or stored automatically.
Future<SavedConnection?> discoverLocalAgent() async {
  if (!Platform.isLinux) return null;
  final home = Platform.environment['HOME'];
  if (home == null) return null;
  final file = File('$home/.config/lazytunnel-fleet/gui/access-code');
  try {
    final stat = await file.stat();
    if (stat.mode & 0x3f != 0 ||
        stat.size > 1024 ||
        await FileSystemEntity.type(file.path, followLinks: false) !=
            FileSystemEntityType.file) {
      return null;
    }
    return SavedConnection(
      const ConnectionProfile(name: 'This computer', local: true),
      Credentials(accessCode: (await file.readAsString()).trim()),
    );
  } catch (_) {
    return null;
  }
}
