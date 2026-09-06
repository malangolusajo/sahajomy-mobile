import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sahajomy_mobile/core/network/api_client.dart';
import 'package:sahajomy_mobile/core/storage/secure_storage.dart';
import 'package:sahajomy_mobile/core/storage/token_storage.dart';
import 'package:sahajomy_mobile/core/workspaces/workspace_provider.dart';
import 'package:sahajomy_mobile/features/auth/data/auth_repository.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('fresh OTP token, not a stale stored token, verifies auth/me', () async {
    FlutterSecureStorage.setMockInitialValues({
      SecureStorage.accessTokenKey: 'stale-access-token',
      SecureStorage.refreshTokenKey: 'stale-refresh-token',
    });
    final storage = TokenStorage();
    final adapter = _AuthAdapter(role: 'customer', mfaVerified: false);
    final api = ApiClient(
      dio: Dio(BaseOptions(baseUrl: 'https://example.test/api/v1/'))
        ..httpClientAdapter = adapter,
      tokenStorage: storage,
      workspaceProvider: WorkspaceProvider(storage),
      enableLogging: false,
    );

    final step = await AuthRepository(api)
        .verifyOtp(phoneNumber: '+255712345678', otpCode: '123456');

    expect(step, isA<Authenticated>());
    expect(adapter.profileAuthorization, 'Bearer fresh-access-token-123');
    expect(adapter.verifyAuthorization, isNull);
  });

  test(
    'privileged OTP session fails closed without server-confirmed MFA',
    () async {
      FlutterSecureStorage.setMockInitialValues({});
      final storage = TokenStorage();
      final adapter = _AuthAdapter(role: 'super_admin', mfaVerified: false);
      final api = ApiClient(
        dio: Dio(BaseOptions(baseUrl: 'https://example.test/api/v1/'))
          ..httpClientAdapter = adapter,
        tokenStorage: storage,
        workspaceProvider: WorkspaceProvider(storage),
        enableLogging: false,
      );

      await expectLater(
        AuthRepository(api)
            .verifyOtp(phoneNumber: '+255712345678', otpCode: '123456'),
        throwsA(isA<FormatException>()),
      );
    },
  );

  test(
    'MFA challenge remains a challenge and does not create a session',
    () async {
      FlutterSecureStorage.setMockInitialValues({});
      final storage = TokenStorage();
      final adapter = _MfaChallengeAdapter();
      final api = ApiClient(
        dio: Dio(BaseOptions(baseUrl: 'https://example.test/api/v1/'))
          ..httpClientAdapter = adapter,
        tokenStorage: storage,
        workspaceProvider: WorkspaceProvider(storage),
        enableLogging: false,
      );

      final step = await AuthRepository(api)
          .verifyOtp(phoneNumber: '+255712345678', otpCode: '123456');
      expect(step, isA<MfaRequired>());
      expect((step as MfaRequired).challenge.setupRequired, isTrue);
      expect(adapter.profileCalls, 0);
    },
  );
}

class _AuthAdapter implements HttpClientAdapter {
  _AuthAdapter({required this.role, required this.mfaVerified});

  final String role;
  final bool mfaVerified;
  String? verifyAuthorization;
  String? profileAuthorization;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    if (options.path.endsWith('auth/verify-otp')) {
      verifyAuthorization = options.headers['Authorization'] as String?;
      return _response({
        'access_token': 'fresh-access-token-123',
        'refresh_token': 'fresh-refresh-token-123',
      });
    }
    if (options.path.endsWith('auth/me')) {
      profileAuthorization = options.headers['Authorization'] as String?;
      return _response({'role': role, 'mfa_verified': mfaVerified});
    }
    return _response({}, statusCode: 404);
  }

  @override
  void close({bool force = false}) {}
}

class _MfaChallengeAdapter implements HttpClientAdapter {
  int profileCalls = 0;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    if (options.path.endsWith('auth/me')) profileCalls++;
    return _response({
      'mfa_required': true,
      'mfa_setup_required': true,
      'challenge_token': 'single-use-challenge-token',
    });
  }

  @override
  void close({bool force = false}) {}
}

ResponseBody _response(Map<String, dynamic> body, {int statusCode = 200}) =>
    ResponseBody.fromString(
      jsonEncode(body),
      statusCode,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
