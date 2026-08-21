import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config/api_config.dart';
import 'api_exception.dart';

typedef AccessTokenProvider = Future<String?> Function();
typedef RefreshAccessToken = Future<String?> Function();

class ApiClient {
  ApiClient({
    http.Client? client,
    this.accessTokenProvider,
    this.refreshAccessToken,
  }) : _client = client ?? http.Client();

  static Future<String?>? _refreshInFlight;
  final http.Client _client;
  final AccessTokenProvider? accessTokenProvider;
  final RefreshAccessToken? refreshAccessToken;

  Future<Map<String, dynamic>> get(String path) async =>
      (await _send('GET', path)) as Map<String, dynamic>;
  Future<List<Map<String, dynamic>>> getList(String path) async =>
      ((await _send('GET', path)) as List).cast<Map<String, dynamic>>();
  Future<Map<String, dynamic>> post(String path, {Object? body}) async =>
      (await _send('POST', path, body: body)) as Map<String, dynamic>;
  Future<Map<String, dynamic>> put(String path, {Object? body}) async =>
      (await _send('PUT', path, body: body)) as Map<String, dynamic>;

  Future<Object> _send(String method, String path, {Object? body}) async {
    final token = await accessTokenProvider?.call();
    var response = await _sendRequest(method, path, body: body, token: token);
    if (response.statusCode == 401 && refreshAccessToken != null) {
      final refreshedToken = await _refreshToken();
      if (refreshedToken != null && refreshedToken.isNotEmpty) {
        response = await _sendRequest(
          method,
          path,
          body: body,
          token: refreshedToken,
        );
      }
    }
    final bodyText = await response.stream.bytesToString();
    final decoded = bodyText.isEmpty
        ? <String, dynamic>{}
        : jsonDecode(bodyText);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      final errorBody = decoded is Map<String, dynamic>
          ? decoded
          : <String, dynamic>{};
      final message = errorBody['message'] ?? errorBody['detail'];
      throw ApiException(
        statusCode: response.statusCode,
        message: message is String
            ? message
            : 'The request could not be completed.',
        details: errorBody['detail'],
      );
    }
    return decoded;
  }

  Future<String?> _refreshToken() {
    final activeRefresh = _refreshInFlight;
    if (activeRefresh != null) return activeRefresh;
    final refresh = refreshAccessToken!();
    _refreshInFlight = refresh;
    return refresh.whenComplete(() {
      if (identical(_refreshInFlight, refresh)) _refreshInFlight = null;
    });
  }

  Future<http.StreamedResponse> _sendRequest(
    String method,
    String path, {
    Object? body,
    String? token,
  }) {
    final request = http.Request(method, ApiConfig.uri(path))
      ..headers.addAll({
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        if (token != null && token.isNotEmpty) 'Authorization': 'Bearer $token',
      });
    if (body != null) request.body = jsonEncode(body);
    return _client.send(request).timeout(const Duration(seconds: 30));
  }

  void close() => _client.close();
}
