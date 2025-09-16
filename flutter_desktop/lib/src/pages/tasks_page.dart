import 'package:flutter/material.dart';
import '../services/api.dart';

class TasksPage extends StatefulWidget {
  const TasksPage({super.key});

  @override
  State<TasksPage> createState() => _TasksPageState();
}

class _TasksPageState extends State<TasksPage> {
  final TextEditingController _title = TextEditingController();
  final TextEditingController _desc = TextEditingController();
  List<dynamic> _tasks = [];
  bool _loading = true;

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      _tasks = await ApiService.listTasks();
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _addTask() async {
    await ApiService.createTask(title: _title.text.trim(), description: _desc.text.trim());
    _title.clear(); _desc.clear();
    await _load();
  }

  Future<void> _completeTask(String id) async {
    await ApiService.completeTask(id);
    await _load();
  }

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Tasks & Schedule')), 
      body: Row(
        children: [
          Expanded(
            flex: 2,
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Create Task', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 12),
                  TextField(controller: _title, decoration: const InputDecoration(labelText: 'Title')),
                  const SizedBox(height: 8),
                  TextField(controller: _desc, decoration: const InputDecoration(labelText: 'Description')),
                  const SizedBox(height: 12),
                  FilledButton(
                    onPressed: _addTask,
                    child: const Text('Add Task'),
                  ),
                  const SizedBox(height: 24),
                  const Divider(),
                  const SizedBox(height: 12),
                  const Text('Upcoming Events (Create)', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 8),
                  FilledButton.icon(
                    onPressed: () async {
                      // Minimal demo event creation
                      await ApiService.createEvent(
                        calendarId: 'primary', title: 'Demo Event', start: DateTime.now().toIso8601String(),
                        end: DateTime.now().add(const Duration(hours: 1)).toIso8601String(),
                      );
                      if (!mounted) return;
                      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Demo event created')));
                    },
                    icon: const Icon(Icons.add_alert),
                    label: const Text('Create Demo Event'),
                  ),
                ],
              ),
            ),
          ),
          const VerticalDivider(width: 1),
          Expanded(
            flex: 3,
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : ListView.separated(
                      itemCount: _tasks.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 8),
                      itemBuilder: (context, index) {
                        final t = _tasks[index] as Map<String, dynamic>;
                        final id = t['id'] ?? t['doc_id'] ?? '';
                        final title = t['title'] ?? '';
                        final status = t['status'] ?? 'pending';
                        return ListTile(
                          title: Text(title),
                          subtitle: Text('Status: $status'),
                          trailing: status == 'pending'
                              ? IconButton(
                                  icon: const Icon(Icons.check_circle_outline),
                                  tooltip: 'Mark complete',
                                  onPressed: () => _completeTask(id),
                                )
                              : const Icon(Icons.check_circle, color: Colors.greenAccent),
                        );
                      },
                    ),
            ),
          ),
        ],
      ),
    );
  }
}

