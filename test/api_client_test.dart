import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sahajomy_mobile/core/network/api_client.dart';
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
        'Bearer refreshed-token',
      ]);
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
        'access_token': 'refreshed-token',
        'refresh_token': 'refresh-token-2',
      });
    }
    protectedTokens.add(options.headers['Authorization'] as String?);
    if (options.headers['Authorization'] == 'Bearer refreshed-token') {
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
