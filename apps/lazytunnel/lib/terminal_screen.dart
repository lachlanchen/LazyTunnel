import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:lazytunnel_client/lazytunnel_client.dart';
import 'package:xterm/xterm.dart';

class TerminalScreen extends StatefulWidget {
  final AgentConnection connection;
  final Device device;
  const TerminalScreen({
    super.key,
    required this.connection,
    required this.device,
  });
  @override
  State<TerminalScreen> createState() => _TerminalScreenState();
}

class _TerminalScreenState extends State<TerminalScreen> {
  final terminal = Terminal(maxLines: 5000);
  final focus = FocusNode();
  ShellSession? session;
  final List<StreamSubscription<String>> subscriptions = [];
  String status = 'Connecting';
  @override
  void initState() {
    super.initState();
    connect();
  }

  Future<void> connect() async {
    try {
      final s = await widget.connection.terminal(
        widget.device.name,
        width: terminal.viewWidth,
        height: terminal.viewHeight,
      );
      if (!mounted) {
        s.close();
        return;
      }
      session = s;
      subscriptions.add(
        s.output.listen(terminal.write, onError: (_) => ended()),
      );
      subscriptions.add(
        s.errors.listen(terminal.write, onError: (_) => ended()),
      );
      terminal.onOutput = s.write;
      terminal.onResize = s.resize;
      setState(() => status = 'Connected');
      focus.requestFocus();
      await s.done;
      ended();
    } catch (e) {
      terminal.write('\r\n$e\r\n');
      ended();
    }
  }

  void ended() {
    terminal.onOutput = null;
    if (mounted) setState(() => status = 'Session ended');
  }

  @override
  void dispose() {
    terminal.onOutput = null;
    terminal.onResize = null;
    for (final s in subscriptions) {
      s.cancel();
    }
    session?.close();
    focus.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text('${widget.device.name} · $status'),
      actions: [
        IconButton(
          tooltip: 'Paste clipboard',
          icon: const Icon(Icons.content_paste),
          onPressed: () async {
            final data = await Clipboard.getData(Clipboard.kTextPlain);
            if (mounted && status == 'Connected' && data?.text != null) {
              terminal.paste(data!.text!);
            }
          },
        ),
      ],
    ),
    body: SafeArea(
      child: Column(
        children: [
          Expanded(
            child: TerminalView(
              terminal,
              focusNode: focus,
              autofocus: true,
              backgroundOpacity: 1,
              padding: const EdgeInsets.all(12),
            ),
          ),
          Material(
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  for (final item in <(String, String)>[
                    ('Esc', '\x1b'),
                    ('Tab', '\t'),
                    ('Ctrl C', '\x03'),
                    ('Ctrl D', '\x04'),
                    ('Ctrl L', '\x0c'),
                    ('↑', '\x1b[A'),
                    ('↓', '\x1b[B'),
                    ('←', '\x1b[D'),
                    ('→', '\x1b[C'),
                  ])
                    TextButton(
                      onPressed: status == 'Connected'
                          ? () {
                              session?.write(item.$2);
                              focus.requestFocus();
                            }
                          : null,
                      child: Text(item.$1),
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    ),
  );
}
