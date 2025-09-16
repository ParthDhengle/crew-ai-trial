import 'dart:io';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import '../services/api.dart';

class PowerBiPage extends StatefulWidget {
  const PowerBiPage({super.key});

  @override
  State<PowerBiPage> createState() => _PowerBiPageState();
}

class _PowerBiPageState extends State<PowerBiPage> {
  String? _tempPath;
  final TextEditingController _query = TextEditingController(text: 'Create suitable visuals from my data.');
  bool _autoOpen = false;
  bool _busy = false;
  String? _status;

  Future<void> _pickFile() async {
    final res = await FilePicker.platform.pickFiles(type: FileType.custom, allowedExtensions: ['csv', 'xlsx', 'xls']);
    if (res == null || res.files.single.path == null) return;
    final filePath = res.files.single.path!;
    setState(() { _busy = true; _status = 'Uploading ${res.files.single.name}...'; });
    try {
      final temp = await ApiService.powerBiUpload(File(filePath));
      setState(() { _tempPath = temp; _status = 'Uploaded. Ready to generate.'; });
    } catch (e) {
      setState(() { _status = 'Upload failed: $e'; });
    } finally {
      if (mounted) setState(() { _busy = false; });
    }
  }

  Future<void> _generate() async {
    if (_tempPath == null) {
      setState(() { _status = 'Please upload a CSV/XLSX first.'; });
      return;
    }
    setState(() { _busy = true; _status = 'Generating Power BI dashboard...'; });
    try {
      final msg = await ApiService.powerBiGenerate(tempPath: _tempPath!, query: _query.text.trim(), autoOpen: _autoOpen);
      setState(() { _status = msg; });
    } catch (e) {
      setState(() { _status = 'Generate failed: $e'; });
    } finally {
      if (mounted) setState(() { _busy = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Power BI Assistant'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                FilledButton.icon(
                  onPressed: _busy ? null : _pickFile,
                  icon: const Icon(Icons.upload_file),
                  label: const Text('Upload CSV/XLSX'),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(_tempPath == null ? 'No file uploaded' : 'Temp file ready'),
                )
              ],
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _query,
              minLines: 2,
              maxLines: 4,
              decoration: const InputDecoration(labelText: 'Describe the visualization you want'),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Switch(value: _autoOpen, onChanged: (v) => setState(() => _autoOpen = v)),
                const Text('Auto-open in Power BI (asks OS to open)')
              ],
            ),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: _busy ? null : _generate,
              icon: const Icon(Icons.auto_graph),
              label: const Text('Generate Dashboard'),
            ),
            const SizedBox(height: 16),
            if (_status != null)
              Text(_status!),
          ],
        ),
      ),
    );
  }
}

