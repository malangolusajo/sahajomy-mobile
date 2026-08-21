import '../auth/session_store.dart';
import 'api_client.dart';

ApiClient authenticatedApiClient(SessionStore store) => ApiClient(
  accessTokenProvider: () async => (await store.read())?.accessToken,
  refreshAccessToken: () async {
    final session = await store.read();
    if (session == null) return null;
    try {
      final response = await ApiClient().post(
        'auth/refresh',
        body: {'refresh_token': session.refreshToken},
      );
      final accessToken = response['access_token'] as String?;
      if (accessToken == null || accessToken.isEmpty) return null;
      await store.save(
        session.copyWith(
          accessToken: accessToken,
          refreshToken: response['refresh_token'] as String?,
        ),
      );
      return accessToken;
    } catch (_) {
      return null;
    }
  },
);
