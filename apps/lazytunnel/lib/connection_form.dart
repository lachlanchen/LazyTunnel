import 'package:flutter/material.dart';
import 'package:lazytunnel_client/lazytunnel_client.dart';
import 'profile_store.dart';

class ConnectionForm extends StatefulWidget {
  final SavedConnection? initial;
  final bool localDefault;
  final Future<void> Function(SavedConnection, bool) onConnect;
  const ConnectionForm({
    super.key,
    this.initial,
    this.localDefault = false,
    required this.onConnect,
  });
  @override
  State<ConnectionForm> createState() => _ConnectionFormState();
}

class _ConnectionFormState extends State<ConnectionForm> {
  final _form = GlobalKey<FormState>();
  final Map<String, TextEditingController> fields = {};
  bool local = false, remember = false, jumping = false, busy = false;
  String? error;
  TextEditingController field(String key) =>
      fields.putIfAbsent(key, TextEditingController.new);
  @override
  void initState() {
    super.initState();
    final p = widget.initial?.profile;
    final c = widget.initial?.credentials;
    local = p?.local ?? widget.localDefault;
    jumping = p?.jump != null;
    final initial = {
      'name': p?.name ?? 'My computers',
      'host': p?.host ?? '127.0.0.1',
      'port': '${p?.sshPort ?? 22}',
      'user': p?.username ?? '',
      'fingerprint': p?.fingerprint ?? '',
      'agent': '${p?.agentPort ?? 17766}',
      'code': c?.accessCode ?? '',
      'password': c?.password ?? '',
      'key': c?.privateKey ?? '',
      'passphrase': c?.passphrase ?? '',
      'jhost': p?.jump?.host ?? '',
      'jport': '${p?.jump?.sshPort ?? 2222}',
      'juser': p?.jump?.username ?? '',
      'jfingerprint': p?.jump?.fingerprint ?? '',
      'jpassword': c?.jump?.password ?? '',
      'jkey': c?.jump?.privateKey ?? '',
      'jpassphrase': c?.jump?.passphrase ?? '',
    };
    for (final entry in initial.entries) {
      field(entry.key).text = entry.value;
    }
  }

  @override
  void dispose() {
    for (final c in fields.values) {
      c.dispose();
    }
    super.dispose();
  }

  Widget input(
    String id,
    String label, {
    String? hint,
    bool secret = false,
    bool numeric = false,
    bool optional = false,
    int lines = 1,
  }) => Padding(
    padding: const EdgeInsets.only(bottom: 16),
    child: TextFormField(
      key: ValueKey(id),
      controller: field(id),
      obscureText: secret && lines == 1,
      minLines: lines,
      maxLines: lines,
      autocorrect: false,
      enableSuggestions: false,
      keyboardType: numeric
          ? TextInputType.number
          : lines > 1
          ? TextInputType.multiline
          : TextInputType.text,
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        border: const OutlineInputBorder(),
      ),
      validator: (v) =>
          !optional && (v == null || v.trim().isEmpty) ? 'Required' : null,
    ),
  );

  Future<void> submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      String value(String key) => field(key).text.trim();
      final jump = !local && jumping
          ? ConnectionProfile(
              name: 'Jump host',
              host: value('jhost'),
              sshPort: int.parse(value('jport')),
              username: value('juser'),
              fingerprint: value('jfingerprint'),
            )
          : null;
      final profile = ConnectionProfile(
        name: value('name'),
        local: local,
        host: local ? '127.0.0.1' : value('host'),
        sshPort: int.parse(value('port')),
        username: value('user'),
        fingerprint: value('fingerprint'),
        agentPort: int.parse(value('agent')),
        jump: jump,
      );
      profile.validate();
      final credentials = Credentials(
        accessCode: value('code'),
        password: field('password').text,
        privateKey: field('key').text,
        passphrase: field('passphrase').text,
        jump: jump == null
            ? null
            : Credentials(
                password: field('jpassword').text,
                privateKey: field('jkey').text,
                passphrase: field('jpassphrase').text,
              ),
      );
      await widget.onConnect(SavedConnection(profile, credentials), remember);
    } catch (e) {
      if (mounted) setState(() => error = '$e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Form(
    key: _form,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'Connect your workspace',
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        const SizedBox(height: 8),
        const Text(
          'Your own server. Your existing computers. One private control room.',
        ),
        const SizedBox(height: 24),
        input('name', 'Connection name'),
        SegmentedButton<bool>(
          segments: const [
            ButtonSegment(
              value: true,
              label: Text('This device'),
              icon: Icon(Icons.computer),
            ),
            ButtonSegment(
              value: false,
              label: Text('Through SSH'),
              icon: Icon(Icons.lock_outline),
            ),
          ],
          selected: {local},
          onSelectionChanged: busy
              ? null
              : (v) => setState(() => local = v.first),
        ),
        const SizedBox(height: 20),
        if (local)
          const Padding(
            padding: EdgeInsets.only(bottom: 20),
            child: Text(
              'The local agent listens on loopback only. Install it with “lazytunnel agent install”.',
            ),
          ),
        if (!local) ...[
          input('host', 'Controller SSH host', hint: 'IP address or hostname'),
          Row(
            children: [
              Expanded(child: input('port', 'SSH port', numeric: true)),
              const SizedBox(width: 12),
              Expanded(child: input('user', 'Username')),
            ],
          ),
          input('fingerprint', 'Verified host fingerprint', hint: 'SHA256:…'),
          const Padding(
            padding: EdgeInsets.only(bottom: 18),
            child: SelectableText(
              'Verify on the controller:\nssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub\nA changed key is always rejected.',
            ),
          ),
          input('password', 'SSH password', secret: true, optional: true),
          ExpansionTile(
            title: const Text('Private key instead of password'),
            children: [
              input('key', 'OpenSSH private key', lines: 4, optional: true),
              input(
                'passphrase',
                'Key passphrase',
                secret: true,
                optional: true,
              ),
            ],
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Use a cloud jump host'),
            subtitle: const Text(
              'Reach a private controller through its relay.',
            ),
            value: jumping,
            onChanged: (v) => setState(() => jumping = v),
          ),
          if (jumping) ...[
            input('jhost', 'Jump host'),
            Row(
              children: [
                Expanded(child: input('jport', 'Jump SSH port', numeric: true)),
                const SizedBox(width: 12),
                Expanded(child: input('juser', 'Jump username')),
              ],
            ),
            input('jfingerprint', 'Jump host fingerprint', hint: 'SHA256:…'),
            input('jpassword', 'Jump password', secret: true, optional: true),
            ExpansionTile(
              title: const Text('Jump private key'),
              children: [
                input(
                  'jkey',
                  'Jump OpenSSH private key',
                  lines: 4,
                  optional: true,
                ),
                input(
                  'jpassphrase',
                  'Jump key passphrase',
                  secret: true,
                  optional: true,
                ),
              ],
            ),
          ],
        ],
        const SizedBox(height: 12),
        input('agent', 'Agent port', numeric: true),
        input(
          'code',
          'Agent access code',
          secret: true,
          hint: 'Run: lazytunnel agent code',
        ),
        CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Remember in secure storage'),
          subtitle: const Text(
            'Uses Keychain, Keystore or this computer’s secret store.',
          ),
          value: remember,
          onChanged: busy ? null : (v) => setState(() => remember = v ?? false),
        ),
        if (error != null)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 12),
            child: SelectableText(
              error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ),
        const SizedBox(height: 12),
        FilledButton.icon(
          onPressed: busy ? null : submit,
          icon: busy
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.arrow_forward),
          label: Text(busy ? 'Connecting…' : 'Connect'),
        ),
      ],
    ),
  );
}
