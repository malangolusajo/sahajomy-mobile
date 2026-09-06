import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/auth/session.dart';
import '../../../core/auth/mfa_challenge.dart';
import '../../../core/network/api_client.dart';
import '../../../core/providers.dart';

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return AuthRepository(apiClient);
});

sealed class AuthenticationStep {
  const AuthenticationStep();
}

class Authenticated extends AuthenticationStep {
  const Authenticated(this.session);
  final Session session;
}

/// Deliberately memory-only. Never persist or place this material in a URL.
class MfaRequired extends AuthenticationStep {
  const MfaRequired(this.challenge);
  final MfaChallenge challenge;
}

class AuthRepository {
  AuthRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<void> sendOtp({
    required String phoneNumber,
    String? name,
    String? email,
  }) async {
    await _apiClient.post(
      'auth/send-otp',
      data: {
        'phone_number': phoneNumber,
        if (name != null && name.isNotEmpty) 'name': name,
        if (email != null && email.isNotEmpty) 'email': email,
      },
      options: ApiClient.publicOptions(),
    );
  }

  Future<AuthenticationStep> verifyOtp({
    required String phoneNumber,
    required String otpCode,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      'auth/verify-otp',
      data: {'phone_number': phoneNumber, 'otp_code': otpCode},
      options: ApiClient.publicOptions(),
    );
    return _authenticationStepFrom(response);
  }

  Future<MfaChallenge> loadMfaSetup(MfaChallenge challenge) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      'auth/mfa/setup',
      data: {'challenge_token': challenge.challengeToken},
      options: ApiClient.publicOptions(),
    );
    return challenge.copyWith(
      otpAuthUri: _firstString(response, const [
        'otpauth_uri',
        'otp_auth_uri',
        'qr_uri',
      ]),
      manualSecret: _firstString(response, const ['manual_secret', 'secret']),
    );
  }

  Future<Session> verifyMfa({
    required MfaChallenge challenge,
    required String code,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      'auth/mfa/verify',
      data: {'challenge_token': challenge.challengeToken, 'code': code},
      options: ApiClient.publicOptions(),
    );
    return _sessionFromTokens(response, mfaConfirmed: true);
  }

  Future<Session> verifyStoredSession(Session session) async {
    final profile = await _apiClient.get<Map<String, dynamic>>(
      'auth/me',
      options: Options(extra: {'skipTenant': true}),
    );
    final latestAccessToken = await _apiClient.tokenStorage.getAccessToken();
    final latestRefreshToken = await _apiClient.tokenStorage.getRefreshToken();
    if (!_validToken(latestAccessToken) || !_validToken(latestRefreshToken)) {
      throw const FormatException('The stored session is incomplete.');
    }
    return _sessionFromProfile(
      Session(
        accessToken: latestAccessToken!,
        refreshToken: latestRefreshToken!,
        role: session.role,
      ),
      profile,
    );
  }

  Future<Map<String, dynamic>> getProfile() =>
      _apiClient.get<Map<String, dynamic>>('auth/me');

  Future<void> logout(Session session) => _apiClient.post(
    'auth/logout',
    data: {'refresh_token': session.refreshToken},
    options: ApiClient.neverReplayOptions(skipTenant: true),
  );

  Future<AuthenticationStep> _authenticationStepFrom(
    Map<String, dynamic> response,
  ) async {
    final challengeToken = _firstString(response, const [
      'challenge_token',
      'mfa_challenge_token',
    ]);
    final requiresMfa =
        response['mfa_required'] == true ||
        response['requires_mfa'] == true ||
        challengeToken != null;
    if (requiresMfa) {
      if (challengeToken == null || challengeToken.length < 16) {
        throw const FormatException(
          'The server returned an invalid MFA challenge.',
        );
      }
      return MfaRequired(
        MfaChallenge(
          challengeToken: challengeToken,
          setupRequired:
              response['mfa_setup_required'] == true ||
              response['setup_required'] == true,
          otpAuthUri: _firstString(response, const [
            'otpauth_uri',
            'otp_auth_uri',
            'qr_uri',
          ]),
          manualSecret: _firstString(response, const [
            'manual_secret',
            'secret',
          ]),
        ),
      );
    }
    return Authenticated(await _sessionFromTokens(response));
  }

  Future<Session> _sessionFromTokens(
    Map<String, dynamic> response, {
    bool mfaConfirmed = false,
  }) async {
    final accessToken = response['access_token'] as String?;
    final refreshToken = response['refresh_token'] as String?;
    if (!_validToken(accessToken) || !_validToken(refreshToken)) {
      throw const FormatException(
        'The server did not return a complete session.',
      );
    }
    final profile = await _apiClient.get<Map<String, dynamic>>(
      'auth/me',
      options: ApiClient.freshSessionOptions(accessToken!),
    );
    final roleName = profile['role'] as String?;
    if (roleName == null) {
      throw const FormatException('The server did not return a user role.');
    }
    final role = userRoleFromApi(roleName);
    final profileMfaVerified =
        profile['mfa_verified'] == true || profile['mfa_authenticated'] == true;
    if (role != UserRole.customer && !mfaConfirmed && !profileMfaVerified) {
      throw const FormatException(
        'Privileged accounts require server-confirmed multi-factor authentication.',
      );
    }
    return Session(
      accessToken: accessToken,
      refreshToken: refreshToken!,
      role: role,
    );
  }

  Session _sessionFromProfile(Session session, Map<String, dynamic> profile) {
    final roleName = profile['role'] as String?;
    if (roleName == null) {
      throw const FormatException('The server did not return a user role.');
    }
    final role = userRoleFromApi(roleName);
    if (role != UserRole.customer &&
        profile['mfa_verified'] != true &&
        profile['mfa_authenticated'] != true) {
      throw const FormatException(
        'This privileged session is not protected by multi-factor authentication.',
      );
    }
    return session.copyWith(role: role);
  }

  static String? _firstString(
    Map<String, dynamic> response,
    List<String> keys,
  ) {
    for (final key in keys) {
      final value = response[key];
      if (value is String && value.trim().isNotEmpty) return value.trim();
    }
    return null;
  }

  static bool _validToken(String? value) =>
      value != null &&
      value.length >= 16 &&
      value.length <= 16384 &&
      !value.contains(RegExp(r'\s'));
}
