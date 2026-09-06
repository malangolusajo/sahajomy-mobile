import '../storage/token_storage.dart';
import '../storage/secure_storage.dart';
import 'session.dart';

class SessionStore {
  SessionStore(this._tokenStorage);

  final TokenStorage _tokenStorage;

  Future<Session?> read() async {
    final accessToken = await _tokenStorage.getAccessToken();
    final refreshToken = await _tokenStorage.getRefreshToken();
    final roleName = await _tokenStorage.getUserRole();

    if (accessToken == null || refreshToken == null || roleName == null) {
      return null;
    }

    final roles = UserRole.values.where((role) => role.name == roleName);
    if (roles.isEmpty) return null;

    return Session(
      accessToken: accessToken,
      refreshToken: refreshToken,
      role: roles.first,
    );
  }

  Future<void> save(Session session) async {
    await _tokenStorage.saveTokens(
      accessToken: session.accessToken,
      refreshToken: session.refreshToken,
    );
    await _tokenStorage.write(SecureStorage.roleKey, session.role.name);
  }

  Future<void> clear() => _tokenStorage.clear();
}
