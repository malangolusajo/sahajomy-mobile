import 'dart:async';
import 'dart:math';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:logger/logger.dart';

import '../config/api_config.dart';
import '../storage/token_storage.dart';
import '../workspaces/workspace_provider.dart';
import 'api_exception.dart';
import 'interceptors/auth_interceptor.dart';
import 'interceptors/logging_interceptor.dart';
import 'interceptors/refresh_interceptor.dart';
import 'interceptors/tenant_interceptor.dart';

final Logger _logger = Logger();

class ApiClient {
  ApiClient({
    Dio? dio,
    required this.tokenStorage,
    required this.workspaceProvider,
    bool enableLogging = kDebugMode,
  }) : _dio = dio ?? _createDio() {
    // Central response mapping must also apply to injected/testing Dio clients.
    _dio.options.validateStatus = (status) => status != null;
    _setupInterceptors(enableLogging: enableLogging);
  }

  static Dio _createDio() => Dio(
    BaseOptions(
      baseUrl:
          '${ApiConfig.validatedBaseUri().toString().replaceFirst(RegExp(r'/$'), '')}/',
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 30),
      sendTimeout: const Duration(minutes: 5),
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      // All HTTP responses are mapped centrally into actionable ApiExceptions.
      validateStatus: (status) => status != null,
    ),
  );

  final Dio _dio;
  final TokenStorage tokenStorage;
  final WorkspaceProvider workspaceProvider;
  final Random _random = Random.secure();
  Future<void>? _activeRefresh;

  void _setupInterceptors({required bool enableLogging}) {
    _dio.interceptors.addAll([
      if (enableLogging) LoggingInterceptor(_logger),
      TenantInterceptor(workspaceProvider),
      AuthInterceptor(tokenStorage),
      RefreshInterceptor(this),
    ]);
  }

  Dio get dio => _dio;

  /// Public authentication calls must not inherit an old account or tenant.
  static Options publicOptions({bool neverReplay = true}) => Options(
    extra: {
      'skipAuth': true,
      'skipTenant': true,
      if (neverReplay) 'skipRefresh': true,
    },
  );

  /// Validates a newly issued token before it is committed to secure storage.
  static Options freshSessionOptions(String accessToken) => Options(
    headers: {'Authorization': 'Bearer $accessToken'},
    extra: {'skipAuth': true, 'skipTenant': true, 'skipRefresh': true},
  );

  /// Sensitive state changes are never automatically replayed after a 401.
  static Options neverReplayOptions({bool skipTenant = false}) =>
      Options(extra: {'skipRefresh': true, if (skipTenant) 'skipTenant': true});

  Future<void> refreshAccessTokenOnce() {
    final existing = _activeRefresh;
    if (existing != null) return existing;
    final refresh = refreshAccessToken();
    _activeRefresh = refresh;
    return refresh.whenComplete(() {
      if (identical(_activeRefresh, refresh)) _activeRefresh = null;
    });
  }

  Future<void> refreshAccessToken() async {
    final refreshToken = await tokenStorage.getRefreshToken();
    if (refreshToken == null || refreshToken.isEmpty) {
      throw Exception('No refresh token available');
    }

    try {
      final response = await _dio.post(
        'auth/refresh',
        data: {'refresh_token': refreshToken},
        options: Options(
          headers: {'Content-Type': 'application/json'},
          // Refresh is an auth-scoped request. It must not inherit a stale
          // bearer token or the previously selected tenant context.
          extra: {'skipAuth': true, 'skipTenant': true, 'skipRefresh': true},
        ),
      );

      final statusCode = response.statusCode ?? 0;
      if (statusCode < 200 || statusCode >= 300) {
        if (statusCode == 400 || statusCode == 401 || statusCode == 403) {
          await tokenStorage.clear();
        }
        throw ApiException(
          statusCode: statusCode,
          message: _errorMessage(statusCode),
        );
      }
      final body = response.data;
      if (body is! Map) {
        await tokenStorage.clear();
        throw const FormatException('Invalid refresh response.');
      }
      final accessToken = body['access_token'] as String?;
      final newRefreshToken = body['refresh_token'] as String?;

      if (!_validToken(accessToken) ||
          (newRefreshToken != null && !_validToken(newRefreshToken))) {
        throw const FormatException('Invalid token in refresh response.');
      }

      await tokenStorage.saveTokens(
        accessToken: accessToken!,
        refreshToken: newRefreshToken ?? refreshToken,
      );
    } on FormatException {
      await tokenStorage.clear();
      rethrow;
    }
  }

  Future<T> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    final response = await _dio.get<T>(
      _validatedPath(path),
      queryParameters: queryParameters,
      options: options,
    );
    return _handleResponse(response);
  }

  Future<List<Map<String, dynamic>>> getList(
    String path, {
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    final response = await _dio.get<List<dynamic>>(
      _validatedPath(path),
      queryParameters: queryParameters,
      options: options,
    );
    return _handleListResponse(response);
  }

  Future<Map<String, dynamic>> getObject(
    String path, {
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    final response = await _dio.get<Map<String, dynamic>>(
      _validatedPath(path),
      queryParameters: queryParameters,
      options: options,
    );
    return _handleObjectResponse(response);
  }

  Future<T> post<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    final response = await _dio.post<T>(
      _validatedPath(path),
      data: data,
      queryParameters: queryParameters,
      options: _mutationOptions(options),
    );
    return _handleResponse(response);
  }

  Future<T> put<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    final response = await _dio.put<T>(
      _validatedPath(path),
      data: data,
      queryParameters: queryParameters,
      options: _mutationOptions(options),
    );
    return _handleResponse(response);
  }

  Future<T> patch<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    final response = await _dio.patch<T>(
      _validatedPath(path),
      data: data,
      queryParameters: queryParameters,
      options: _mutationOptions(options),
    );
    return _handleResponse(response);
  }

  Future<T> delete<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    final response = await _dio.delete<T>(
      _validatedPath(path),
      queryParameters: queryParameters,
      options: _mutationOptions(options),
    );
    return _handleResponse(response);
  }

  Future<T> postForm<T>(
    String path, {
    required FormData data,
    Options? options,
  }) async {
    final response = await _dio.post<T>(
      _validatedPath(path),
      data: data,
      options: _mutationOptions(options),
    );
    return _handleResponse(response);
  }

  Options _mutationOptions(Options? options) {
    final headers = <String, dynamic>{
      ...?options?.headers,
      'Idempotency-Key': _newIdempotencyKey(),
    };
    return (options ?? Options()).copyWith(headers: headers);
  }

  String _newIdempotencyKey() {
    final randomPart = List.generate(
      16,
      (_) => _random.nextInt(256).toRadixString(16).padLeft(2, '0'),
    ).join();
    return '${DateTime.now().microsecondsSinceEpoch}-$randomPart';
  }

  String _validatedPath(String path) {
    final uri = Uri.tryParse(path);
    if (path.isEmpty ||
        path.length > 2048 ||
        uri == null ||
        uri.hasScheme ||
        uri.hasAuthority ||
        uri.hasQuery ||
        uri.hasFragment ||
        path.startsWith('/') ||
        path.contains('\\') ||
        path.split('/').any((segment) => segment == '..') ||
        path.contains(RegExp(r'[\x00-\x1F\x7F]'))) {
      throw ArgumentError.value(path.length, 'path', 'Invalid API path.');
    }
    return path;
  }

  bool _validToken(String? value) =>
      value != null &&
      value.length >= 16 &&
      value.length <= 16384 &&
      !value.contains(RegExp(r'\s'));

  T _handleResponse<T>(Response<dynamic> response) {
    if (response.statusCode == null ||
        response.statusCode! < 200 ||
        response.statusCode! >= 300) {
      throw ApiException(
        statusCode: response.statusCode ?? 0,
        message: _errorMessage(response.statusCode ?? 0),
      );
    }
    return response.data as T;
  }

  List<Map<String, dynamic>> _handleListResponse(Response<dynamic> response) {
    if (response.statusCode == null ||
        response.statusCode! < 200 ||
        response.statusCode! >= 300) {
      throw ApiException(
        statusCode: response.statusCode ?? 0,
        message: _errorMessage(response.statusCode ?? 0),
      );
    }
    final data = response.data as List<dynamic>?;
    return data?.cast<Map<String, dynamic>>() ?? <Map<String, dynamic>>[];
  }

  Map<String, dynamic> _handleObjectResponse(Response<dynamic> response) {
    if (response.statusCode == null ||
        response.statusCode! < 200 ||
        response.statusCode! >= 300) {
      throw ApiException(
        statusCode: response.statusCode ?? 0,
        message: _errorMessage(response.statusCode ?? 0),
      );
    }
    return response.data as Map<String, dynamic>? ?? <String, dynamic>{};
  }

  void close() => _dio.close();

  String _errorMessage(int statusCode) {
    return switch (statusCode) {
      401 => 'Your session has expired. Sign in again to continue.',
      403 => 'You do not have permission for this action.',
      409 => 'This action conflicts with the latest server state.',
      410 => 'This link or code has expired. Request a new one.',
      422 => 'Check the highlighted information and try again.',
      429 => 'Too many requests. Wait a moment and try again.',
      >= 500 => 'Sahajomy is temporarily unavailable. Try again shortly.',
      _ => 'The request could not be completed.',
    };
  }
}
