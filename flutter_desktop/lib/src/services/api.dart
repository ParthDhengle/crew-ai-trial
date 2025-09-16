import 'dart:io';

import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  static String baseUrl = 'http://127.0.0.1:8001';

  static Future<Map<String, dynamic>> _getJson(String path, {Map<String, String>? params}) async {
    final uri = Uri.parse('$baseUrl$path').replace(queryParameters: params);
    final res = await http.get(uri);
    if (res.statusCode >= 200 && res.statusCode < 300) {
      return json.decode(res.body) as Map<String, dynamic>;
    }
    throw Exception('GET $path failed: ${res.statusCode} ${res.body}');
  }

  static Future<Map<String, dynamic>> _postJson(String path, Map<String, dynamic> body) async {
    final uri = Uri.parse('$baseUrl$path');
    final res = await http.post(uri, headers: {'Content-Type': 'application/json'}, body: json.encode(body));
    if (res.statusCode >= 200 && res.statusCode < 300) {
      return json.decode(res.body) as Map<String, dynamic>;
    }
    throw Exception('POST $path failed: ${res.statusCode} ${res.body}');
  }

  static Future<Map<String, dynamic>> _patchJson(String path, Map<String, dynamic> body) async {
    final uri = Uri.parse('$baseUrl$path');
    final res = await http.patch(uri, headers: {'Content-Type': 'application/json'}, body: json.encode(body));
    if (res.statusCode >= 200 && res.statusCode < 300) {
      return json.decode(res.body) as Map<String, dynamic>;
    }
    throw Exception('PATCH $path failed: ${res.statusCode} ${res.body}');
  }

  // Profile
  static Future<void> upsertProfile({required String name, required String email}) async {
    await _postJson('/profile', {
      'name': name,
      'email': email,
    });
  }

  // Chat
  static Future<String> processQuery(String query) async {
    final data = await _postJson('/process_query', {'query': query});
    return (data['result'] ?? '').toString();
  }

  // Tasks
  static Future<List<dynamic>> listTasks() async {
    final uri = Uri.parse('$baseUrl/tasks');
    final res = await http.get(uri);
    if (res.statusCode >= 200 && res.statusCode < 300) {
      return json.decode(res.body) as List<dynamic>;
    }
    throw Exception('GET /tasks failed: ${res.statusCode} ${res.body}');
  }

  static Future<String> createTask({required String title, String? description}) async {
    final data = await _postJson('/tasks', {
      'title': title,
      'description': description,
    });
    return (data['id'] ?? '').toString();
    
  }

  static Future<void> completeTask(String id) async {
    await _postJson('/tasks/$id/complete', {});
  }

  // Events
  static Future<void> createEvent({required String calendarId, required String title, required String start, required String end}) async {
    await _postJson('/events', {
      'calendar_id': calendarId,
      'title': title,
      'start': start,
      'end': end,
    });
  }

  // Power BI
  static Future<String> powerBiUpload(File file) async {
    final uri = Uri.parse('$baseUrl/powerbi/upload');
    final req = http.MultipartRequest('POST', uri);
    req.files.add(await http.MultipartFile.fromPath('file', file.path));
    final res = await req.send();
    final body = await res.stream.bytesToString();
    if (res.statusCode >= 200 && res.statusCode < 300) {
      final data = json.decode(body) as Map<String, dynamic>;
      return (data['temp_path'] ?? '').toString();
    }
    throw Exception('Upload failed: ${res.statusCode} $body');
  }

  static Future<String> powerBiGenerate({required String tempPath, required String query, required bool autoOpen}) async {
    final uri = Uri.parse('$baseUrl/powerbi/generate');
    final res = await http.post(uri, headers: {'Content-Type': 'application/x-www-form-urlencoded'}, body: {
      'temp_path': tempPath,
      'query': query,
      'auto_open': autoOpen ? 'true' : 'false',
    });
    if (res.statusCode >= 200 && res.statusCode < 300) {
      final data = json.decode(res.body) as Map<String, dynamic>;
      return (data['message'] ?? '').toString();
    }
    throw Exception('Generate failed: ${res.statusCode} ${res.body}');
  }
}

