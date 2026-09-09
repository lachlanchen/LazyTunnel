import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';

/// Only forwarded application content is a WebView. The management UI is native.
class ViewerScreen extends StatefulWidget {
  final Uri uri;
  final String name;
  const ViewerScreen({super.key, required this.uri, required this.name});
  @override
  State<ViewerScreen> createState() => _ViewerScreenState();
}

class _ViewerScreenState extends State<ViewerScreen> {
  late final WebViewController controller;
  String? error;
  int progress = 0;
  @override
  void initState() {
    super.initState();
    controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(
        NavigationDelegate(
          onProgress: (value) {
            if (mounted) setState(() => progress = value);
          },
          onNavigationRequest: (request) {
            final target = Uri.tryParse(request.url);
            // Do not let a forwarded page turn into arbitrary native navigation.
            return target?.scheme == widget.uri.scheme &&
                    target?.host == widget.uri.host &&
                    target?.port == widget.uri.port
                ? NavigationDecision.navigate
                : NavigationDecision.prevent;
          },
          onWebResourceError: (e) {
            if (mounted && e.isForMainFrame == true) {
              setState(() => error = e.description);
            }
          },
        ),
      )
      ..loadRequest(widget.uri);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text(widget.name),
      actions: [
        IconButton(
          tooltip: 'Reload viewer',
          onPressed: () {
            setState(() => error = null);
            controller.reload();
          },
          icon: const Icon(Icons.refresh),
        ),
      ],
    ),
    body: SafeArea(
      child: Column(
        children: [
          if (progress < 100) LinearProgressIndicator(value: progress / 100),
          if (error != null)
            Padding(padding: const EdgeInsets.all(12), child: Text(error!)),
          Expanded(child: WebViewWidget(controller: controller)),
        ],
      ),
    ),
  );
}
