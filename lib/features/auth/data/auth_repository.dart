import '../../../core/auth/session.dart';
import '../../../core/network/api_client.dart';

class AuthRepository {
  AuthRepository({ApiClient? client}) : _client = client ?? ApiClient();

  final ApiClient _client;

  Future<void> sendOtp({
    required String phoneNumber,
    String? name,
    String? email,
  }) async {
    await _client.post(
      'auth/send-otp',
      body: {
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
    final tokenResponse = await _client.post(
      'auth/verify-otp',
      body: {'phone_number': phoneNumber, 'otp_code': otpCode},
    );
    final accessToken = tokenResponse['access_token'] as String?;
    final refreshToken = tokenResponse['refresh_token'] as String?;
    if (accessToken == null || refreshToken == null) {
      throw const FormatException(
        'The server did not return a complete session.',
      );
    }

    return verifySession(
      Session(
        accessToken: accessToken,
        refreshToken: refreshToken,
        role: userRoleFromApi(
          (tokenResponse['user'] as Map<String, dynamic>?)?['role']
                  as String? ??
              'customer',
        ),
      ),
    );
  }

  Future<Session> verifySession(Session session) async {
    final verifiedClient = ApiClient(
      accessTokenProvider: () async => session.accessToken,
    );
    final profile = await verifiedClient.get('auth/me');
    final role = profile['role'] as String?;
    if (role == null) {
      throw const FormatException('The server did not return a user role.');
    }
    return session.copyWith(role: userRoleFromApi(role));
  }

  Future<Map<String, dynamic>> getProfile(Session session) =>
      ApiClient(accessTokenProvider: () async => session.accessToken)
          .get('auth/me');

  Future<Session> refreshSession(Session session) async {
    final response = await _client.post(
      'auth/refresh',
      body: {'refresh_token': session.refreshToken},
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

  Future<void> logout(Session session) => _client.post(
    'auth/logout',
    body: {'refresh_token': session.refreshToken},
  );
}
