import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class SecureStorage {
  SecureStorage({FlutterSecureStorage? storage})
    : _storage =
          storage ??
          const FlutterSecureStorage(
            aOptions: AndroidOptions(migrateWithBackup: true),
            iOptions: IOSOptions(
              accessibility: KeychainAccessibility.unlocked_this_device,
              synchronizable: false,
            ),
          );

  static const accessTokenKey = 'access_token';
  static const refreshTokenKey = 'refresh_token';
  static const roleKey = 'user_role';
  static const companyIdKey = 'company_id';
  static const branchIdKey = 'branch_id';
  static const userIdKey = 'user_id';
  static const onboardingCompletedKey = 'onboarding_completed';
  static const onboardingVersionKey = 'onboarding_version';

  final FlutterSecureStorage _storage;

  Future<String?> read(String key) => _storage.read(key: key);

  Future<void> write(String key, String value) =>
      _storage.write(key: key, value: value);

  Future<void> delete(String key) => _storage.delete(key: key);
}
