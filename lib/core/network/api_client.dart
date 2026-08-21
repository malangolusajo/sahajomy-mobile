import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config/api_config.dart';
import 'api_exception.dart';

typedef AccessTokenProvider = Future<String?> Function();

class ApiClient {
  ApiClient({http.Client? client, this.accessTokenProvider})
    : _client = client ?? http.Client();

  final http.Client _client;
  final AccessTokenProvider? accessTokenProvider;

  Future<Map<String, dynamic>> get(String path) => _send('GET', path);
  Future<Map<String, dynamic>> post(String path, {Object? body}) =>
      _send('POST', path, body: body);

  Future<Map<String, dynamic>> _send(
    String method,
    String path, {
    Object? body,
  }) async {
    final token = await accessTokenProvider?.call();
    final request = http.Request(method, ApiConfig.uri(path))
      ..headers.addAll({
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        if (token != null && token.isNotEmpty) 'Authorization': 'Bearer $token',
      });
    if (body != null) request.body = jsonEncode(body);
    final response = await _client
        .send(request)
        .timeout(const Duration(seconds: 30));
    final bodyText = await response.stream.bytesToString();
    final decoded = bodyText.isEmpty
        ? <String, dynamic>{}
        : jsonDecode(bodyText) as Map<String, dynamic>;
    if (response.statusCode < 200 || response.statusCode >= 300) {
      final message = decoded['message'] ?? decoded['detail'];
      throw ApiException(
        statusCode: response.statusCode,
        message: message is String
            ? message
            : 'The request could not be completed.',
        details: decoded['detail'],
      );
    }
    return decoded;
  }

  void close() => _client.close();
}
