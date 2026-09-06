import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sahajomy_mobile/core/network/api_client.dart';
import 'package:sahajomy_mobile/core/network/api_exception.dart';
import 'package:sahajomy_mobile/core/storage/secure_storage.dart';
import 'package:sahajomy_mobile/core/storage/token_storage.dart';
import 'package:sahajomy_mobile/core/workspaces/workspace_provider.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test(
    'retries one protected request after refreshing an expired token',
    () async {
      FlutterSecureStorage.setMockInitialValues({
        SecureStorage.accessTokenKey: 'expired-token',
        SecureStorage.refreshTokenKey: 'refresh-token',
      });
      final storage = TokenStorage();
      final adapter = _RefreshAdapter();
      final dio = Dio(
        BaseOptions(
          baseUrl: 'https://example.test/api/v1/',
          validateStatus: (status) => status != null && status < 500,
        ),
      )..httpClientAdapter = adapter;
      final api = ApiClient(
        dio: dio,
        tokenStorage: storage,
        workspaceProvider: WorkspaceProvider(storage),
        enableLogging: false,
      );

      final response = await api.get<Map<String, dynamic>>(
        'protected-resource',
      );

      expect(response['ok'], isTrue);
      expect(adapter.refreshCalls, 1);
      expect(adapter.protectedTokens, [
        'Bearer expired-token',
        'Bearer refreshed-access-token',
      ]);
      expect(await storage.getAccessToken(), 'refreshed-access-token');
      expect(await storage.getRefreshToken(), 'refreshed-refresh-token');
    },
  );

  test('adds tenant headers and an idempotency key to mutations', () async {
    FlutterSecureStorage.setMockInitialValues({});
    final storage = TokenStorage();
    final workspace = WorkspaceProvider(storage);
    await workspace.setWorkspace(
      companyId: 'company-1',
      companyName: 'Cargo Co',
      branchId: 'branch-1',
    );
    final adapter = _CaptureAdapter();
    final dio = Dio(BaseOptions(baseUrl: 'https://example.test/api/v1/'))
      ..httpClientAdapter = adapter;
    final api = ApiClient(
      dio: dio,
      tokenStorage: storage,
      workspaceProvider: workspace,
      enableLogging: false,
    );

    await api.post<Map<String, dynamic>>('mutation', data: {'value': 1});

    expect(adapter.options?.headers['X-Sahajomy-Company'], 'company-1');
    expect(adapter.options?.headers['X-Sahajomy-Branch'], 'branch-1');
    expect(adapter.options?.headers['Idempotency-Key'], isNotEmpty);
  });

  test('public auth calls cannot inherit account or tenant headers', () async {
    FlutterSecureStorage.setMockInitialValues({
      SecureStorage.accessTokenKey: 'stored-access-token',
      SecureStorage.refreshTokenKey: 'stored-refresh-token',
    });
    final storage = TokenStorage();
    final workspace = WorkspaceProvider(storage);
    await workspace.setWorkspace(
      companyId: 'company-1',
      companyName: 'Cargo Co',
      branchId: 'branch-1',
    );
    final adapter = _CaptureAdapter();
    final dio = Dio(BaseOptions(baseUrl: 'https://example.test/api/v1/'))
      ..httpClientAdapter = adapter;
    final api = ApiClient(
      dio: dio,
      tokenStorage: storage,
      workspaceProvider: workspace,
      enableLogging: false,
    );

    await api.post<Map<String, dynamic>>(
      'auth/send-otp',
      data: {'phone_number': '+255712345678'},
      options: ApiClient.publicOptions(),
    );

    expect(adapter.options?.headers['Authorization'], isNull);
    expect(adapter.options?.headers['X-Sahajomy-Company'], isNull);
    expect(adapter.options?.headers['X-Sahajomy-Branch'], isNull);
    expect(adapter.options?.extra['skipRefresh'], isTrue);
  });

  test('server error text is never reflected into the UI exception', () async {
    FlutterSecureStorage.setMockInitialValues({});
    final storage = TokenStorage();
    final dio = Dio(BaseOptions(baseUrl: 'https://example.test/api/v1/'))
      ..httpClientAdapter = _ErrorAdapter();
    final api = ApiClient(
      dio: dio,
      tokenStorage: storage,
      workspaceProvider: WorkspaceProvider(storage),
      enableLogging: false,
    );

    await expectLater(
      api.getObject('unsafe-error'),
      throwsA(
        isA<ApiException>()
            .having(
              (error) => error.message,
              'message',
              'The request could not be completed.',
            )
            .having((error) => error.details, 'details', isNull),
      ),
    );
  });

  test(
    'transient refresh failure does not destroy the stored session',
    () async {
      FlutterSecureStorage.setMockInitialValues({
        SecureStorage.accessTokenKey: 'stored-access-token',
        SecureStorage.refreshTokenKey: 'stored-refresh-token',
      });
      final storage = TokenStorage();
      final dio = Dio(
        BaseOptions(
          baseUrl: 'https://example.test/api/v1/',
          validateStatus: (status) => status != null,
        ),
      )..httpClientAdapter = _UnavailableRefreshAdapter();
      final api = ApiClient(
        dio: dio,
        tokenStorage: storage,
        workspaceProvider: WorkspaceProvider(storage),
        enableLogging: false,
      );

      await expectLater(
        api.getObject('protected'),
        throwsA(isA<ApiException>()),
      );
      expect(await storage.getAccessToken(), 'stored-access-token');
      expect(await storage.getRefreshToken(), 'stored-refresh-token');
    },
  );
}

class _ErrorAdapter implements HttpClientAdapter {
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async => _jsonResponse(400, {
    'message': 'Token SECRET_VALUE and internal stack trace',
  });

  @override
  void close({bool force = false}) {}
}

class _UnavailableRefreshAdapter implements HttpClientAdapter {
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    if (options.path.endsWith('auth/refresh')) {
      return _jsonResponse(503, {'message': 'database details'});
    }
    return _jsonResponse(401, {'message': 'expired'});
  }

  @override
  void close({bool force = false}) {}
}

class _RefreshAdapter implements HttpClientAdapter {
  int refreshCalls = 0;
  final protectedTokens = <String?>[];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    if (options.path.endsWith('auth/refresh')) {
      refreshCalls++;
      return _jsonResponse(200, {
        'access_token': 'refreshed-access-token',
        'refresh_token': 'refreshed-refresh-token',
      });
    }
    protectedTokens.add(options.headers['Authorization'] as String?);
    if (options.headers['Authorization'] == 'Bearer refreshed-access-token') {
      return _jsonResponse(200, {'ok': true});
    }
    return _jsonResponse(401, {'detail': 'Expired token'});
  }

  @override
  void close({bool force = false}) {}
}

class _CaptureAdapter implements HttpClientAdapter {
  RequestOptions? options;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    this.options = options;
    return _jsonResponse(200, {'ok': true});
  }

  @override
  void close({bool force = false}) {}
}

ResponseBody _jsonResponse(int statusCode, Map<String, dynamic> body) =>
    ResponseBody.fromString(
      jsonEncode(body),
      statusCode,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
