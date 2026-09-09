import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:lazytunnel_client/lazytunnel_client.dart';
import 'package:url_launcher/url_launcher.dart';
import 'connection_form.dart';
import 'profile_store.dart';
import 'terminal_screen.dart';
import 'viewer_screen.dart';

class LazyTunnelApp extends StatefulWidget {
  final ProfileStore store;
  final Future<SavedConnection?> Function() discoverLocal;
  const LazyTunnelApp({
    super.key,
    required this.store,
    this.discoverLocal = discoverLocalAgent,
  });
  @override
  State<LazyTunnelApp> createState() => _LazyTunnelAppState();
}

class _LazyTunnelAppState extends State<LazyTunnelApp> {
  ThemeMode mode = ThemeMode.system;
  ThemeData theme(Brightness brightness) {
    final scheme = ColorScheme.fromSeed(
      seedColor: const Color(0xff176b5b),
      brightness: brightness,
    );
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: brightness == Brightness.light
          ? const Color(0xfff5f7f6)
          : const Color(0xff111b1a),
      cardTheme: CardThemeData(
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: BorderSide(color: scheme.outlineVariant),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 18),
        ),
      ),
      inputDecorationTheme: const InputDecorationTheme(filled: true),
    );
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'LazyTunnel',
    debugShowCheckedModeBanner: false,
    theme: theme(Brightness.light),
    darkTheme: theme(Brightness.dark),
    themeMode: mode,
    home: Workspace(
      store: widget.store,
      discoverLocal: widget.discoverLocal,
      onTheme: () => setState(
        () => mode = mode == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark,
      ),
    ),
  );
}

class Workspace extends StatefulWidget {
  final ProfileStore store;
  final VoidCallback onTheme;
  final Future<SavedConnection?> Function() discoverLocal;
  const Workspace({super.key, required this.store, required this.onTheme, required this.discoverLocal});
  @override
  State<Workspace> createState() => _WorkspaceState();
}

class _WorkspaceState extends State<Workspace> with WidgetsBindingObserver {
  AgentConnection? connection;
  Snapshot? snapshot;
  List<SavedConnection> saved = [];
  SavedConnection? draft;
  String? message;
  String search = '';
  int page = 0;
  bool refreshing = false, loading = true, background = false;
  Timer? poll;
  static const labels = ['Overview', 'Computers', 'Viewers', 'Connections'];
  static const icons = [
    Icons.space_dashboard_outlined,
    Icons.devices_outlined,
    Icons.open_in_browser,
    Icons.tune,
  ];
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    load();
  }

  Future<void> load() async {
    try {
      saved = await widget.store.load();
    } catch (_) {
      message =
          'Secure storage is unavailable. You can connect for this visit without saving credentials.';
    }
    draft = await widget.discoverLocal();
    if (mounted) setState(() => loading = false);
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    background =
        state == AppLifecycleState.paused ||
        state == AppLifecycleState.detached;
    if (background) {
      poll?.cancel();
    } else if (state == AppLifecycleState.resumed) {
      refresh();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    poll?.cancel();
    connection?.close();
    super.dispose();
  }

  void notify(String text) {
    if (mounted) setState(() => message = text);
  }

  Future<void> connect(SavedConnection item, bool remember) async {
    final next = await AgentConnection.connect(item.profile, item.credentials);
    if (!mounted) {
      await next.close();
      return;
    }
    final old = connection;
    setState(() {
      connection = next;
      draft = item;
      message = null;
      page = 0;
      snapshot = null;
    });
    await old?.close();
    if (remember) {
      final list = [
        ...saved.where((p) => p.profile.name != item.profile.name),
        item,
      ];
      try {
        await widget.store.save(list);
        saved = list;
      } catch (_) {
        notify(
          'Connected for this visit. Secure storage could not save this profile.',
        );
      }
    }
    await refresh();
  }

  Future<void> refresh() async {
    final active = connection;
    if (active == null || refreshing || background) return;
    refreshing = true;
    try {
      final next = await active.api.snapshot();
      if (mounted && connection == active) setState(() => snapshot = next);
      poll?.cancel();
      if (next.checking && !background) {
        poll = Timer(const Duration(seconds: 2), refresh);
      }
    } catch (e) {
      notify('$e');
    } finally {
      refreshing = false;
    }
  }

  Future<void> action(Future<void> Function() work) async {
    try {
      await work();
      await refresh();
    } catch (e) {
      notify('$e');
    }
  }

  Future<void> disconnect() async {
    poll?.cancel();
    final active = connection;
    setState(() {
      connection = null;
      snapshot = null;
      message = null;
      page = 0;
    });
    await active?.close();
  }

  Future<void> copy(String text) async {
    await Clipboard.setData(ClipboardData(text: text));
    if (mounted) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Copied')));
    }
  }

  Future<void> open(Viewer viewer) async {
    try {
      final uri = await connection!.viewerUri(viewer);
      if (!mounted) return;
      if (Platform.isAndroid || Platform.isIOS) {
        await Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) => ViewerScreen(uri: uri, name: viewer.name),
          ),
        );
      } else if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
        notify('Browser could not open. Viewer address: $uri');
      }
    } catch (e) {
      notify('$e');
    }
  }

  Future<void> terminal(Device device) async {
    if (connection!.supportsTerminal) {
      await Navigator.of(context).push(
        MaterialPageRoute<void>(
          builder: (_) =>
              TerminalScreen(connection: connection!, device: device),
        ),
      );
    } else if (Platform.isLinux) {
      try {
        await Process.start('x-terminal-emulator', [
          '-e',
          'ssh',
          '-F',
          '${Platform.environment['HOME']}/.config/lazytunnel-fleet/ssh_config',
          'lazy-${device.name}',
        ], mode: ProcessStartMode.detached);
      } catch (_) {
        notify('Open a terminal and run: ssh lazy-${device.name}');
      }
    } else {
      await copy('ssh lazy-${device.name}');
    }
  }

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final connected = connection != null;
    return Scaffold(
      appBar: AppBar(
        title: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.hub_outlined),
            SizedBox(width: 10),
            Text('LazyTunnel'),
          ],
        ),
        actions: [
          if (connected)
            IconButton(
              tooltip: 'Refresh state',
              onPressed: refresh,
              icon: const Icon(Icons.refresh),
            ),
          IconButton(
            tooltip: 'Light or dark theme',
            onPressed: widget.onTheme,
            icon: const Icon(Icons.brightness_6_outlined),
          ),
          const SizedBox(width: 8),
        ],
      ),
      bottomNavigationBar: connected && width < 800
          ? NavigationBar(
              selectedIndex: page,
              onDestinationSelected: (i) => setState(() => page = i),
              destinations: [
                for (var i = 0; i < labels.length; i++)
                  NavigationDestination(icon: Icon(icons[i]), label: labels[i]),
              ],
            )
          : null,
      body: SafeArea(
        child: Row(
          children: [
            if (connected && width >= 800)
              NavigationRail(
                selectedIndex: page,
                extended: width >= 1180,
                onDestinationSelected: (i) => setState(() => page = i),
                destinations: [
                  for (var i = 0; i < labels.length; i++)
                    NavigationRailDestination(
                      icon: Icon(icons[i]),
                      label: Text(labels[i]),
                    ),
                ],
              ),
            Expanded(
              child: loading
                  ? const Center(child: CircularProgressIndicator())
                  : Center(
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 1400),
                        child: ListView(
                          padding: EdgeInsets.all(width < 600 ? 18 : 30),
                          children: [
                            if (message != null)
                              Card(
                                color: Theme.of(
                                  context,
                                ).colorScheme.errorContainer,
                                child: Padding(
                                  padding: const EdgeInsets.all(14),
                                  child: Row(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Expanded(child: SelectableText(message!)),
                                      IconButton(
                                        tooltip: 'Dismiss',
                                        onPressed: () =>
                                            setState(() => message = null),
                                        icon: const Icon(Icons.close),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            if (message != null) const SizedBox(height: 20),
                            if (!connected) ...[
                              if (saved.isNotEmpty) ...[
                                Text(
                                  'Saved connections',
                                  style: Theme.of(context).textTheme.titleLarge,
                                ),
                                const SizedBox(height: 12),
                                ...saved.map(
                                  (s) => ListTile(
                                    leading: const Icon(Icons.lock_outline),
                                    title: Text(s.profile.name),
                                    subtitle: Text(
                                      s.profile.local
                                          ? 'Local agent'
                                          : s.profile.host,
                                    ),
                                    trailing: const Icon(Icons.arrow_forward),
                                    onTap: () =>
                                        action(() => connect(s, false)),
                                  ),
                                ),
                                const SizedBox(height: 24),
                              ],
                              Center(
                                child: ConstrainedBox(
                                  constraints: const BoxConstraints(
                                    maxWidth: 640,
                                  ),
                                  child: Card(
                                    child: Padding(
                                      padding: const EdgeInsets.all(24),
                                      child: ConnectionForm(
                                        initial: draft,
                                        localDefault: Platform.isLinux,
                                        onConnect: connect,
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                            ] else if (page == 3)
                              ...connections()
                            else ...[
                              ...header(),
                              if (snapshot == null)
                                const Center(child: CircularProgressIndicator())
                              else ...[
                                if (page == 0) ...overview(),
                                if (page == 1) ...computers(),
                                if (page == 2) ...viewers(),
                              ],
                            ],
                          ],
                        ),
                      ),
                    ),
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> header() => [
    Wrap(
      alignment: WrapAlignment.spaceBetween,
      runSpacing: 12,
      spacing: 20,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              page == 0 ? 'Your computers, connected.' : labels[page],
              style: Theme.of(
                context,
              ).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 8),
            Text(
              '${connection!.profile.name} · ${connection!.profile.local ? 'Local agent' : 'Verified SSH'}',
            ),
          ],
        ),
        FilledButton.tonalIcon(
          onPressed: snapshot?.checking == true
              ? null
              : () => action(() => connection!.api.check()),
          icon: const Icon(Icons.network_check),
          label: Text(
            snapshot?.checking == true ? 'Checking…' : 'Check connections',
          ),
        ),
      ],
    ),
    const SizedBox(height: 26),
  ];
  List<Widget> overview() {
    final s = snapshot!;
    return [
      grid([
        stat('${s.devices.length}', 'Computers', Icons.devices_outlined),
        stat(
          '${s.devices.where((d) => d.status == 'reachable').length}',
          'Verified reachable',
          Icons.check_circle_outline,
        ),
        stat(
          '${s.viewers.where((v) => v.available).length}',
          'Viewer entries ready',
          Icons.open_in_browser,
        ),
      ], minimum: 230),
      const SizedBox(height: 28),
      Text('Quick access', style: Theme.of(context).textTheme.titleLarge),
      const SizedBox(height: 14),
      grid(s.devices.take(6).map(deviceCard).toList()),
      const SizedBox(height: 28),
      Card(
        child: Padding(
          padding: const EdgeInsets.all(22),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(Icons.shield_outlined),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'The core keeps running.',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'Closing this app leaves the agent and its persistent forwards running. Native SSH terminals and the app’s viewer connections end when you disconnect. On phones, keep the app in the foreground while using them.',
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    ];
  }

  Widget stat(String value, String label, IconData icon) => Card(
    child: Padding(
      padding: const EdgeInsets.all(22),
      child: Row(
        children: [
          Icon(icon, size: 30, color: Theme.of(context).colorScheme.primary),
          const SizedBox(width: 18),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(value, style: Theme.of(context).textTheme.headlineMedium),
                Text(label),
              ],
            ),
          ),
        ],
      ),
    ),
  );
  Widget grid(List<Widget> children, {double minimum = 300}) => LayoutBuilder(
    builder: (context, constraints) {
      final count = (constraints.maxWidth / minimum).floor().clamp(1, 4);
      final width = (constraints.maxWidth - (count - 1) * 16) / count;
      return Wrap(
        spacing: 16,
        runSpacing: 16,
        children: children
            .map((child) => SizedBox(width: width, child: child))
            .toList(),
      );
    },
  );
  List<Widget> computers() => [
    TextField(
      decoration: const InputDecoration(
        prefixIcon: Icon(Icons.search),
        hintText: 'Find a computer',
        border: OutlineInputBorder(),
      ),
      onChanged: (v) => setState(() => search = v.toLowerCase()),
    ),
    const SizedBox(height: 20),
    grid(
      snapshot!.devices
          .where(
            (d) => '${d.name} ${d.user} ${d.aliases.join(' ')}'
                .toLowerCase()
                .contains(search),
          )
          .map(deviceCard)
          .toList(),
    ),
  ];
  Widget deviceCard(Device d) => Card(
    child: Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(d.local ? Icons.home_work_outlined : Icons.computer),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  d.name,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
              Icon(
                Icons.circle,
                size: 10,
                color: d.status == 'reachable'
                    ? Colors.teal
                    : d.status == 'unreachable'
                    ? Colors.orange
                    : Colors.grey,
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text('${d.user}${d.local ? ' · Controller' : ''}'),
          const SizedBox(height: 16),
          Text(
            d.status == 'reachable'
                ? 'SSH verified · ${d.latencyMs} ms'
                : d.detail,
          ),
          const SizedBox(height: 18),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              FilledButton.tonalIcon(
                onPressed: () => terminal(d),
                icon: const Icon(Icons.terminal, size: 18),
                label: const Text('Terminal'),
              ),
              IconButton(
                tooltip: 'Copy SSH command',
                onPressed: () => copy('ssh lazy-${d.name}'),
                icon: const Icon(Icons.copy, size: 20),
              ),
              IconButton(
                tooltip: 'Check this computer',
                onPressed: () => action(() => connection!.api.check(d.name)),
                icon: const Icon(Icons.network_check, size: 20),
              ),
            ],
          ),
        ],
      ),
    ),
  );

  List<Widget> viewers() => [
    Wrap(
      spacing: 12,
      runSpacing: 12,
      children: [
        FilledButton.icon(
          onPressed: addViewer,
          icon: const Icon(Icons.add),
          label: const Text('Add viewer'),
        ),
        const Padding(
          padding: EdgeInsets.all(12),
          child: Text('noVNC and private web apps, through your own relay.'),
        ),
      ],
    ),
    const SizedBox(height: 20),
    if (snapshot!.viewers.isEmpty)
      const Card(
        child: Padding(
          padding: EdgeInsets.all(28),
          child: Text(
            'Add an existing local web app, or forward a port from an enrolled computer.',
          ),
        ),
      ),
    grid(
      snapshot!.viewers
          .map(
            (v) => Card(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.web_asset_outlined, size: 30),
                    const SizedBox(height: 12),
                    Text(v.name, style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 8),
                    Text('${v.device} · ${v.remotePort} → ${v.localPort}'),
                    const SizedBox(height: 8),
                    Text(
                      v.mode == 'local'
                          ? 'Existing app · owned by its original service'
                          : 'Forward ${v.status}',
                    ),
                    const SizedBox(height: 16),
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: [
                        FilledButton.tonalIcon(
                          onPressed: v.available ? () => open(v) : null,
                          icon: const Icon(Icons.open_in_new, size: 18),
                          label: const Text('Open'),
                        ),
                        if (v.mode != 'local')
                          TextButton(
                            onPressed: () => action(
                              () => connection!.api.action(
                                v.id,
                                v.status == 'active' ? 'stop' : 'start',
                              ),
                            ),
                            child: Text(
                              v.status == 'active' ? 'Stop' : 'Start',
                            ),
                          ),
                        IconButton(
                          tooltip: 'Remove saved viewer',
                          onPressed: () async {
                            final yes = await showDialog<bool>(
                              context: context,
                              builder: (ctx) => AlertDialog(
                                title: const Text('Remove this viewer?'),
                                content: const Text(
                                  'This removes the saved card. Stop an active managed forward first.',
                                ),
                                actions: [
                                  TextButton(
                                    onPressed: () => Navigator.pop(ctx, false),
                                    child: const Text('Cancel'),
                                  ),
                                  TextButton(
                                    onPressed: () => Navigator.pop(ctx, true),
                                    child: const Text('Remove'),
                                  ),
                                ],
                              ),
                            );
                            if (yes == true) {
                              await action(
                                () => connection!.api.action(v.id, 'remove'),
                              );
                            }
                          },
                          icon: const Icon(Icons.delete_outline, size: 20),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          )
          .toList(),
    ),
  ];

  Future<void> addViewer() async {
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (ctx) => ViewerForm(
        devices: snapshot!.devices,
        managed: snapshot!.managedForwards,
      ),
    );
    if (result != null) {
      await action(
        () => connection!.api.saveViewer(
          name: result['name'] as String,
          device: result['device'] as String,
          remotePort: result['remote_port'] as int,
          localPort: result['local_port'] as int,
          path: result['path'] as String,
          mode: result['mode'] as String,
        ),
      );
    }
  }

  List<Widget> connections() => [
    Text(
      'Connection settings',
      style: Theme.of(context).textTheme.headlineMedium,
    ),
    const SizedBox(height: 18),
    ListTile(
      contentPadding: EdgeInsets.zero,
      title: Text(connection!.profile.name),
      subtitle: Text(
        connection!.profile.local
            ? 'Local controller'
            : '${connection!.profile.username}@${connection!.profile.host} · verified SSH',
      ),
      trailing: OutlinedButton(
        onPressed: disconnect,
        child: const Text('Disconnect'),
      ),
    ),
    const SizedBox(height: 14),
    const Text('Saved securely on this device'),
    const SizedBox(height: 10),
    ...saved.map(
      (item) => ListTile(
        title: Text(item.profile.name),
        subtitle: Text(item.profile.host),
        leading: const Icon(Icons.lock_outline),
        onTap: () => action(() => connect(item, false)),
        trailing: IconButton(
          tooltip: 'Forget saved credentials',
          icon: const Icon(Icons.delete_outline),
          onPressed: () async {
            final list = saved.where((s) => s != item).toList();
            try {
              await widget.store.save(list);
              if (mounted) setState(() => saved = list);
            } catch (_) {
              notify('Secure storage could not remove the profile.');
            }
          },
        ),
      ),
    ),
    const SizedBox(height: 24),
    Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 640),
        child: Card(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: ConnectionForm(initial: draft, onConnect: connect),
          ),
        ),
      ),
    ),
  ];
}

class ViewerForm extends StatefulWidget {
  final List<Device> devices;
  final bool managed;
  const ViewerForm({super.key, required this.devices, required this.managed});
  @override
  State<ViewerForm> createState() => _ViewerFormState();
}

class _ViewerFormState extends State<ViewerForm> {
  final name = TextEditingController(),
      remote = TextEditingController(text: '6080'),
      local = TextEditingController(text: '16080'),
      path = TextEditingController(text: '/vnc.html?resize=scale');
  late String device = widget.devices.first.name;
  bool existing = false;
  String? error;
  @override
  void dispose() {
    for (final c in [name, remote, local, path]) {
      c.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: const Text('Add a private viewer'),
    content: SizedBox(
      width: 500,
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: name,
              decoration: const InputDecoration(labelText: 'Name'),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: device,
              items: widget.devices
                  .map(
                    (d) => DropdownMenuItem(value: d.name, child: Text(d.name)),
                  )
                  .toList(),
              decoration: const InputDecoration(labelText: 'Computer'),
              onChanged: (v) => setState(() {
                device = v!;
                existing = false;
              }),
            ),
            if (widget.devices.firstWhere((d) => d.name == device).local)
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Already running on the controller'),
                value: existing,
                onChanged: (v) => setState(() => existing = v),
              ),
            TextField(
              controller: remote,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Remote web port'),
            ),
            if (!existing)
              TextField(
                controller: local,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Controller local port',
                ),
              ),
            TextField(
              controller: path,
              decoration: const InputDecoration(labelText: 'Viewer path'),
            ),
            if (error != null)
              Text(
                error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
          ],
        ),
      ),
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('Cancel'),
      ),
      FilledButton(
        onPressed: () {
          try {
            if (name.text.trim().isEmpty) {
              throw const FormatException('Enter a name.');
            }
            if (!existing && !widget.managed) {
              throw const FormatException(
                'This controller does not manage persistent forwards.',
              );
            }
            final rp = int.parse(remote.text),
                lp = existing ? rp : int.parse(local.text);
            if (rp < 1 ||
                rp > 65535 ||
                lp < 1024 ||
                lp > 65535 ||
                !path.text.startsWith('/')) {
              throw const FormatException(
                'Enter valid ports and a path starting with /.',
              );
            }
            Navigator.pop(context, {
              'name': name.text.trim(),
              'device': device,
              'remote_port': rp,
              'local_port': lp,
              'path': path.text,
              'mode': existing ? 'local' : 'forward',
            });
          } catch (e) {
            setState(() => error = '$e');
          }
        },
        child: const Text('Save'),
      ),
    ],
  );
}
