import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/auth/session.dart';
import '../../../core/network/api_client.dart';
import '../../../core/providers.dart';

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return AuthRepository(apiClient);
});

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
    );
  }

  Future<Session> verifyOtp({
    required String phoneNumber,
    required String otpCode,
  }) async {
    final tokenResponse = await _apiClient.post<Map<String, dynamic>>(
      'auth/verify-otp',
      data: {'phone_number': phoneNumber, 'otp_code': otpCode},
    );
    final accessToken = tokenResponse['access_token'] as String?;
    final refreshToken = tokenResponse['refresh_token'] as String?;
    if (accessToken == null || refreshToken == null) {
      throw const FormatException(
        'The server did not return a complete session.',
      );
    }

    final userData = tokenResponse['user'] as Map<String, dynamic>?;
    final role = userData?['role'] as String? ?? 'customer';

    return verifySession(
      Session(
        accessToken: accessToken,
        refreshToken: refreshToken,
        role: userRoleFromApi(role),
      ),
    );
  }

  Future<Session> verifySession(Session session) async {
    final profile = await _apiClient.get<Map<String, dynamic>>('auth/me');
    final role = profile['role'] as String?;
    if (role == null) {
      throw const FormatException('The server did not return a user role.');
    }
    return session.copyWith(role: userRoleFromApi(role));
  }

  Future<Map<String, dynamic>> getProfile() =>
      _apiClient.get<Map<String, dynamic>>('auth/me');

  Future<Session> refreshSession(Session session) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      'auth/refresh',
      data: {'refresh_token': session.refreshToken},
    );
    final accessToken = response['access_token'] as String?;
    if (accessToken == null) {
      throw const FormatException('The server did not return an access token.');
    }
    final refreshed = session.copyWith(
      accessToken: accessToken,
      refreshToken: response['refresh_token'] as String?,
    );
    return verifySession(refreshed);
  }

  Future<void> logout(Session session) => _apiClient.post(
    'auth/logout',
    data: {'refresh_token': session.refreshToken},
  );
}
