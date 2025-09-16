import 'package:flutter/material.dart';
import '../services/api.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final TextEditingController _email = TextEditingController();
  final TextEditingController _name = TextEditingController();
  bool _loading = false;
  String? _error;

  Future<void> _login() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await ApiService.upsertProfile(name: _name.text.trim(), email: _email.text.trim());
      if (!mounted) return;
      Navigator.of(context).pushReplacementNamed('/chat');
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Card(
            color: const Color(0xFF141821),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            child: Padding(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text('Welcome back', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 16),
                  TextField(controller: _name, decoration: const InputDecoration(labelText: 'Name')), 
                  const SizedBox(height: 12),
                  TextField(controller: _email, decoration: const InputDecoration(labelText: 'Email')),
                  const SizedBox(height: 20),
                  if (_error != null) Text(_error!, style: const TextStyle(color: Colors.redAccent)),
                  const SizedBox(height: 8),
                  FilledButton(
                    onPressed: _loading ? null : _login,
                    child: _loading ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Text('Continue'),
                  ),
                  const SizedBox(height: 8),
                  TextButton(
                    onPressed: () => Navigator.of(context).pushReplacementNamed('/signup'),
                    child: const Text('Create an account'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

