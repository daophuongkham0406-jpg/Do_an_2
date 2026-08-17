import 'dart:convert';
import 'dart:io';

class ApiConfig {
  static const _configuredHost =
      String.fromEnvironment('API_HOST', defaultValue: '');

  static String get host {
    if (_configuredHost.isNotEmpty) return _configuredHost;
    return Platform.isAndroid ? '10.0.2.2' : '127.0.0.1';
  }

  static String get baseUrl => 'http://$host:5000';
}

class AppUser {
  const AppUser({
    required this.id,
    required this.fullName,
    required this.username,
    required this.role,
    required this.isPremium,
  });

  final String id;
  final String fullName;
  final String username;
  final String role;
  final bool isPremium;

  bool get isAdmin => role == 'admin';

  AppUser copyWith({String? fullName, bool? isPremium}) {
    return AppUser(
      id: id,
      fullName: fullName ?? this.fullName,
      username: username,
      role: role,
      isPremium: isPremium ?? this.isPremium,
    );
  }

  factory AppUser.fromJson(Map<String, dynamic> json) {
    return AppUser(
      id: (json['id'] ?? json['_id'] ?? '').toString(),
      fullName: (json['fullName'] ?? 'User').toString(),
      username: (json['username'] ?? '').toString(),
      role: (json['role'] ?? 'user').toString(),
      isPremium: json['isPremium'] == true,
    );
  }
}

class ApiResult {
  const ApiResult({
    required this.ok,
    required this.statusCode,
    required this.body,
    this.message,
  });

  final bool ok;
  final int statusCode;
  final dynamic body;
  final String? message;
}

class ApiService {
  const ApiService();

  Future<ApiResult> get(String path) => _request('GET', path);
  Future<ApiResult> delete(String path) => _request('DELETE', path);
  Future<ApiResult> post(String path, Map<String, Object?> body) {
    return _request('POST', path, body: body);
  }

  Future<ApiResult> put(String path, Map<String, Object?> body) {
    return _request('PUT', path, body: body);
  }

  Future<ApiResult> _request(
    String method,
    String path, {
    Map<String, Object?>? body,
    String? baseUrl,
  }) async {
    final client = HttpClient()
      ..connectionTimeout = const Duration(seconds: 12);

    final resolvedBaseUrl = baseUrl ?? ApiConfig.baseUrl;
    final uri = Uri.parse('$resolvedBaseUrl$path');

    try {
      final request = await client.openUrl(
        method,
        uri,
      );
      request.headers.contentType = ContentType.json;
      if (body != null) request.write(jsonEncode(body));

      final response = await request.close();
      final text = await response.transform(utf8.decoder).join();
      final decoded = text.isEmpty ? null : jsonDecode(text);
      String? message;
      if (decoded is Map<String, dynamic>) {
        message =
            decoded['message']?.toString() ?? decoded['error']?.toString();
      }

      return ApiResult(
        ok: response.statusCode >= 200 && response.statusCode < 300,
        statusCode: response.statusCode,
        body: decoded,
        message: message,
      );
    } catch (error, stackTrace) {
      // Trả về lỗi chi tiết để dễ debug khi gọi API từ Flutter
      final errorMessage = error.toString();
      final traceMessage =
          stackTrace.toString().split('\n').take(5).join(' | ');
      return ApiResult(
        ok: false,
        statusCode: 0,
        body: null,
        message:
            'Không thể kết nối tới backend $uri. Lỗi: $errorMessage. Stack: $traceMessage',
      );
    } finally {
      client.close(force: true);
    }
  }

  List<Map<String, dynamic>> listFrom(dynamic body) {
    if (body is List) {
      return body
          .whereType<Map>()
          .map((e) => Map<String, dynamic>.from(e))
          .toList();
    }
    if (body is Map && body['data'] is List) {
      return (body['data'] as List)
          .whereType<Map>()
          .map((e) => Map<String, dynamic>.from(e))
          .toList();
    }
    return [];
  }

  Map<String, dynamic> mapFrom(dynamic body) {
    if (body is Map<String, dynamic>) return body;
    if (body is Map) return Map<String, dynamic>.from(body);
    return {};
  }
}
