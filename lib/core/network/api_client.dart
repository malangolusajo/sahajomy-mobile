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
    _setupInterceptors(enableLogging: enableLogging);
  }

  static Dio _createDio() => Dio(
    BaseOptions(
      baseUrl: ApiConfig.baseUrl,
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

      final accessToken = response.data['access_token'] as String?;
      final newRefreshToken = response.data['refresh_token'] as String?;

      if (accessToken == null || accessToken.isEmpty) {
        throw Exception('No access token in refresh response');
      }

      await tokenStorage.saveTokens(
        accessToken: accessToken,
        refreshToken: newRefreshToken ?? refreshToken,
      );
    } catch (e) {
      await tokenStorage.clear();
      rethrow;
    }
  }

  Future<T> get<T>(String path, {Map<String, dynamic>? queryParameters}) async {
    final response = await _dio.get<T>(path, queryParameters: queryParameters);
    return _handleResponse(response);
  }

  Future<List<Map<String, dynamic>>> getList(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    final response = await _dio.get<List<dynamic>>(
      path,
      queryParameters: queryParameters,
    );
    return _handleListResponse(response);
  }

  Future<Map<String, dynamic>> getObject(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    final response = await _dio.get<Map<String, dynamic>>(
      path,
      queryParameters: queryParameters,
    );
    return _handleObjectResponse(response);
  }

  Future<T> post<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
  }) async {
    final response = await _dio.post<T>(
      path,
      data: data,
      queryParameters: queryParameters,
      options: _mutationOptions(),
    );
    return _handleResponse(response);
  }

  Future<T> put<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
  }) async {
    final response = await _dio.put<T>(
      path,
      data: data,
      queryParameters: queryParameters,
      options: _mutationOptions(),
    );
    return _handleResponse(response);
  }

  Future<T> patch<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
  }) async {
    final response = await _dio.patch<T>(
      path,
      data: data,
      queryParameters: queryParameters,
      options: _mutationOptions(),
    );
    return _handleResponse(response);
  }

  Future<T> delete<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    final response = await _dio.delete<T>(
      path,
      queryParameters: queryParameters,
      options: _mutationOptions(),
    );
    return _handleResponse(response);
  }

  Future<T> postForm<T>(String path, {required FormData data}) async {
    final response = await _dio.post<T>(
      path,
      data: data,
      options: _mutationOptions(),
    );
    return _handleResponse(response);
  }

  Options _mutationOptions() =>
      Options(headers: {'Idempotency-Key': _newIdempotencyKey()});

  String _newIdempotencyKey() {
    final randomPart = List.generate(
      16,
      (_) => _random.nextInt(256).toRadixString(16).padLeft(2, '0'),
    ).join();
    return '${DateTime.now().microsecondsSinceEpoch}-$randomPart';
  }

  T _handleResponse<T>(Response<dynamic> response) {
    if (response.statusCode == null ||
        response.statusCode! < 200 ||
        response.statusCode! >= 300) {
      final errorData = response.data is Map<String, dynamic>
          ? response.data as Map<String, dynamic>
          : <String, dynamic>{};
      final message = _errorMessage(response.statusCode ?? 0, errorData);
      throw ApiException(
        statusCode: response.statusCode ?? 0,
        message: message,
        details: errorData['detail'],
      );
    }
    return response.data as T;
  }

  List<Map<String, dynamic>> _handleListResponse(Response<dynamic> response) {
    if (response.statusCode == null ||
        response.statusCode! < 200 ||
        response.statusCode! >= 300) {
      final errorData = response.data is Map<String, dynamic>
          ? response.data as Map<String, dynamic>
          : <String, dynamic>{};
      final message = _errorMessage(response.statusCode ?? 0, errorData);
      throw ApiException(
        statusCode: response.statusCode ?? 0,
        message: message,
        details: errorData['detail'],
      );
    }
    final data = response.data as List<dynamic>?;
    return data?.cast<Map<String, dynamic>>() ?? <Map<String, dynamic>>[];
  }

  Map<String, dynamic> _handleObjectResponse(Response<dynamic> response) {
    if (response.statusCode == null ||
        response.statusCode! < 200 ||
        response.statusCode! >= 300) {
      final errorData = response.data is Map<String, dynamic>
          ? response.data as Map<String, dynamic>
          : <String, dynamic>{};
      final message = _errorMessage(response.statusCode ?? 0, errorData);
      throw ApiException(
        statusCode: response.statusCode ?? 0,
        message: message,
        details: errorData['detail'],
      );
    }
    return response.data as Map<String, dynamic>? ?? <String, dynamic>{};
  }

  void close() => _dio.close();

  String _errorMessage(int statusCode, Map<String, dynamic> data) {
    final serverMessage = data['message'] ?? data['detail'];
    if (serverMessage is String && serverMessage.trim().isNotEmpty) {
      return serverMessage;
    }
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
