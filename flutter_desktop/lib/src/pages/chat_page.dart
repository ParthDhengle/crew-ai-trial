import 'package:flutter/material.dart';
import '../services/api.dart';

class ChatPage extends StatefulWidget {
  const ChatPage({super.key});

  @override
  State<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends State<ChatPage> {
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scroll = ScrollController();
  final List<Map<String, String>> _messages = [];
  bool _sending = false;

  Future<void> _send() async {
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    setState(() {
      _messages.add({"role": "user", "content": text});
      _sending = true;
    });
    _controller.clear();
    try {
      final result = await ApiService.processQuery(text);
      setState(() {
        _messages.add({"role": "assistant", "content": result});
      });
      await Future.delayed(const Duration(milliseconds: 50));
      if (_scroll.hasClients) _scroll.animateTo(_scroll.position.maxScrollExtent + 80, duration: const Duration(milliseconds: 250), curve: Curves.easeOut);
    } catch (e) {
      setState(() {
        _messages.add({"role": "assistant", "content": 'Error: $e'});
      });
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Assistant'),
        actions: [
          IconButton(
            onPressed: () => Navigator.of(context).pushNamed('/tasks'),
            icon: const Icon(Icons.event_available_outlined),
            tooltip: 'Tasks & Schedule',
          ),
          IconButton(
            onPressed: () => Navigator.of(context).pushNamed('/powerbi'),
            icon: const Icon(Icons.dashboard_customize_outlined),
            tooltip: 'Power BI Assistant',
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.separated(
              controller: _scroll,
              padding: const EdgeInsets.all(16),
              itemCount: _messages.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (context, index) {
                final m = _messages[index];
                final isUser = m['role'] == 'user';
                return Align(
                  alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    constraints: const BoxConstraints(maxWidth: 720),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: isUser ? const Color(0xFF2B2F3A) : const Color(0xFF1C222B),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(m['content'] ?? ''),
                  ),
                );
              },
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _controller,
                    onSubmitted: (_) => _send(),
                    decoration: const InputDecoration(hintText: 'Type a message...'),
                  ),
                ),
                const SizedBox(width: 12),
                FilledButton.icon(
                  onPressed: _sending ? null : _send,
                  icon: const Icon(Icons.send),
                  label: const Text('Send'),
                )
              ],
            ),
          )
        ],
      ),
    );
  }
}

