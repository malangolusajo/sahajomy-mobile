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
      if (accessToken != null || refreshToken != null || roleName != null) {
        await clear();
      }
      return null;
    }

    if (!_validToken(accessToken) || !_validToken(refreshToken)) {
      await clear();
      return null;
    }

    final roles = UserRole.values.where((role) => role.name == roleName);
    if (roles.isEmpty) {
      await clear();
      return null;
    }

    return Session(
      accessToken: accessToken,
      refreshToken: refreshToken,
      role: roles.first,
    );
  }

  Future<void> save(Session session) async {
    if (!_validToken(session.accessToken) ||
        !_validToken(session.refreshToken)) {
      throw const FormatException('Refusing to store an invalid session.');
    }
    await _tokenStorage.saveTokens(
      accessToken: session.accessToken,
      refreshToken: session.refreshToken,
    );
    await _tokenStorage.write(SecureStorage.roleKey, session.role.name);
  }

  Future<void> clear() => _tokenStorage.clear();

  bool _validToken(String value) =>
      value.length >= 16 &&
      value.length <= 16384 &&
      !value.contains(RegExp(r'\s'));
}
