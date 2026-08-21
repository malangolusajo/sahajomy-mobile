import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'session.dart';

class SessionStore {
  SessionStore({FlutterSecureStorage? storage})
    : _storage = storage ?? const FlutterSecureStorage();

  static const _accessTokenKey = 'access_token';
  static const _refreshTokenKey = 'refresh_token';
  static const _roleKey = 'user_role';
  final FlutterSecureStorage _storage;

  Future<Session?> read() async {
    final values = await _storage.readAll();
    final accessToken = values[_accessTokenKey];
    final refreshToken = values[_refreshTokenKey];
    final roleName = values[_roleKey];
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

  Future<void> save(Session session) => Future.wait([
    _storage.write(key: _accessTokenKey, value: session.accessToken),
    _storage.write(key: _refreshTokenKey, value: session.refreshToken),
    _storage.write(key: _roleKey, value: session.role.name),
  ]);

  Future<void> clear() => _storage.deleteAll();
}
