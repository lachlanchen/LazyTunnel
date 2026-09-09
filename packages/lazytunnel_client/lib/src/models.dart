/// Public connection settings. Store the credentials separately in a secret store.
class ConnectionProfile {
  final String name;
  final String host;
  final int sshPort;
  final String username;
  final String fingerprint;
  final int agentPort;
  final bool local;
  final ConnectionProfile? jump;

  const ConnectionProfile({
    this.name = 'My relay',
    this.host = '127.0.0.1',
    this.sshPort = 22,
    this.username = '',
    this.fingerprint = '',
    this.agentPort = 17766,
    this.local = false,
    this.jump,
  });

  factory ConnectionProfile.fromJson(Map<String, dynamic> j) =>
      ConnectionProfile(
        name: j['name'] as String,
        host: j['host'] as String,
        sshPort: j['sshPort'] as int,
        username: j['username'] as String,
        fingerprint: j['fingerprint'] as String,
        agentPort: j['agentPort'] as int,
        local: j['local'] as bool,
        jump: j['jump'] == null
            ? null
            : ConnectionProfile.fromJson(
                Map<String, dynamic>.from(j['jump'] as Map),
              ),
      );

  Map<String, dynamic> toJson() => {
    'name': name,
    'host': host,
    'sshPort': sshPort,
    'username': username,
    'fingerprint': fingerprint,
    'agentPort': agentPort,
    'local': local,
    if (jump != null) 'jump': jump!.toJson(),
  };

  void validate() {
    if (name.trim().isEmpty ||
        name.length > 80 ||
        host.trim().isEmpty ||
        host.contains(RegExp(r'[\s/]')) ||
        sshPort < 1 ||
        sshPort > 65535 ||
        agentPort < 1024 ||
        agentPort > 65535) {
      throw ArgumentError('Enter a name, host and valid ports.');
    }
    if (!local &&
        (username.isEmpty ||
            !RegExp(r'^SHA256:[A-Za-z0-9+/]{43}=?$').hasMatch(fingerprint))) {
      throw ArgumentError(
        'SSH requires a username and a verified SHA256 host fingerprint.',
      );
    }
    if (local && host != '127.0.0.1' && host != 'localhost') {
      throw ArgumentError(
        'Direct HTTP is limited to this device. Use SSH for a remote agent.',
      );
    }
    if (jump != null) {
      if (local || jump!.local || jump!.jump != null)
        throw ArgumentError('Use one SSH jump host.');
      jump!.validate();
    }
  }
}

class Credentials {
  final String accessCode;
  final String password;
  final String privateKey;
  final String passphrase;
  final Credentials? jump;
  const Credentials({
    this.accessCode = '',
    this.password = '',
    this.privateKey = '',
    this.passphrase = '',
    this.jump,
  });
  Map<String, dynamic> toJson() => {
    'accessCode': accessCode,
    'password': password,
    'privateKey': privateKey,
    'passphrase': passphrase,
    if (jump != null) 'jump': jump!.toJson(),
  };
  factory Credentials.fromJson(Map<String, dynamic> j) => Credentials(
    accessCode: j['accessCode'] as String? ?? '',
    password: j['password'] as String? ?? '',
    privateKey: j['privateKey'] as String? ?? '',
    passphrase: j['passphrase'] as String? ?? '',
    jump: j['jump'] == null
        ? null
        : Credentials.fromJson(Map<String, dynamic>.from(j['jump'] as Map)),
  );
}

class Device {
  final String name, user, status, detail;
  final List<String> aliases;
  final bool local;
  final int? latencyMs;
  Device.fromJson(Map<String, dynamic> j)
    : name = j['name'] as String,
      user = j['user'] as String? ?? '',
      local = j['local'] == true,
      aliases = List<String>.from(j['aliases'] as List? ?? []),
      status = (j['probe'] as Map?)?['status'] as String? ?? 'unchecked',
      detail =
          (j['probe'] as Map?)?['detail'] as String? ??
          'Check when you need a connection',
      latencyMs = (j['probe'] as Map?)?['ms'] as int?;
}

class Viewer {
  final String id, name, device, mode, status, path;
  final int localPort, remotePort;
  Viewer.fromJson(Map<String, dynamic> j)
    : id = j['id'] as String,
      name = j['name'] as String,
      device = j['device'] as String,
      mode = j['mode'] as String,
      status = j['status'] as String,
      path = j['path'] as String,
      localPort = j['local_port'] as int,
      remotePort = j['remote_port'] as int;
  bool get available => status == 'active' || mode == 'local';
}

class Snapshot {
  final List<Device> devices;
  final List<Viewer> viewers;
  final bool checking, managedForwards;
  Snapshot.fromJson(Map<String, dynamic> j)
    : devices = (j['devices'] as List)
          .map((e) => Device.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList(),
      viewers = (j['viewers'] as List)
          .map((e) => Viewer.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList(),
      checking = j['checking'] == true,
      managedForwards = j['managed_forwards'] == true;
}
