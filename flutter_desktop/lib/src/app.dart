import 'package:flutter/material.dart';
import 'pages/login_page.dart';
import 'pages/signup_page.dart';
import 'pages/chat_page.dart';
import 'pages/tasks_page.dart';
import 'pages/powerbi_page.dart';

class ParthDesktopApp extends StatelessWidget {
  const ParthDesktopApp({super.key});

  @override
  Widget build(BuildContext context) {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: const Color(0xFF6C63FF),
      brightness: Brightness.dark,
    );
    return MaterialApp(
      title: 'Parth Assistant',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: colorScheme,
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFF0F1115),
        textTheme: const TextTheme(
          bodyMedium: TextStyle(fontFamily: 'Inter'),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: const Color(0xFF1A1D24),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide.none,
          ),
        ),
      ),
      initialRoute: '/login',
      routes: {
        '/login': (context) => const LoginPage(),
        '/signup': (context) => const SignupPage(),
        '/chat': (context) => const ChatPage(),
        '/tasks': (context) => const TasksPage(),
        '/powerbi': (context) => const PowerBiPage(),
      },
    );
  }
}

