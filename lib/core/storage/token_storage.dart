import 'secure_storage.dart';

class TokenStorage {
  TokenStorage({SecureStorage? storage})
    : _storage = storage ?? SecureStorage();

  final SecureStorage _storage;

  Future<String?> getAccessToken() =>
      _storage.read(SecureStorage.accessTokenKey);

  Future<String?> getRefreshToken() =>
      _storage.read(SecureStorage.refreshTokenKey);

  Future<String?> getUserRole() => _storage.read(SecureStorage.roleKey);

  Future<String?> getCompanyId() => _storage.read(SecureStorage.companyIdKey);

  Future<String?> getBranchId() => _storage.read(SecureStorage.branchIdKey);

  Future<String?> getUserId() => _storage.read(SecureStorage.userIdKey);

  Future<String?> getMfaSecret() => _storage.read(SecureStorage.mfaSecretKey);

  Future<void> write(String key, String value) => _storage.write(key, value);

  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    await Future.wait([
      _storage.write(SecureStorage.accessTokenKey, accessToken),
      _storage.write(SecureStorage.refreshTokenKey, refreshToken),
    ]);
  }

  Future<void> saveSession({
    required String accessToken,
    required String refreshToken,
    required String role,
    String? companyId,
    String? branchId,
    String? userId,
  }) async {
    await Future.wait([
      _storage.write(SecureStorage.accessTokenKey, accessToken),
      _storage.write(SecureStorage.refreshTokenKey, refreshToken),
      _storage.write(SecureStorage.roleKey, role),
      if (companyId != null)
        _storage.write(SecureStorage.companyIdKey, companyId),
      if (branchId != null) _storage.write(SecureStorage.branchIdKey, branchId),
      if (userId != null) _storage.write(SecureStorage.userIdKey, userId),
    ]);
  }

  Future<void> saveMfaSecret(String secret) =>
      _storage.write(SecureStorage.mfaSecretKey, secret);

  Future<void> saveWorkspace({
    required String companyId,
    String? branchId,
  }) async {
    await _storage.write(SecureStorage.companyIdKey, companyId);
    if (branchId == null || branchId.isEmpty) {
      await _storage.delete(SecureStorage.branchIdKey);
    } else {
      await _storage.write(SecureStorage.branchIdKey, branchId);
    }
  }

  Future<void> clear() => _storage.deleteAll();

  Future<void> clearWorkspace() async {
    await Future.wait([
      _storage.delete(SecureStorage.companyIdKey),
      _storage.delete(SecureStorage.branchIdKey),
    ]);
  }
}
