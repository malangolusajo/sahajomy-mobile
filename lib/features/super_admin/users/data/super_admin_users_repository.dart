import '../../../../core/network/api_client.dart';

class SuperAdminUsersRepository {
  SuperAdminUsersRepository({required this.client});

  final ApiClient client;

  Future<Map<String, dynamic>> listUsers() =>
      client.getObject('super_admin/users');

  Future<Map<String, dynamic>> updateStatus({
    required String userId,
    required String status,
  }) {
    _validateId(userId);
    if (!const {
      'active',
      'inactive',
      'suspended',
      'pending',
    }.contains(status)) {
      throw ArgumentError.value(status, 'status', 'Unsupported status.');
    }
    return client.patch<Map<String, dynamic>>(
      'super_admin/users/${Uri.encodeComponent(userId)}/status',
      data: {'status': status},
      options: ApiClient.neverReplayOptions(),
    );
  }

  Future<Map<String, dynamic>> updateVerification({
    required String userId,
    required bool isVerified,
  }) {
    _validateId(userId);
    return client.patch<Map<String, dynamic>>(
      'super_admin/users/${Uri.encodeComponent(userId)}/verification',
      data: {'is_verified': isVerified},
      options: ApiClient.neverReplayOptions(),
    );
  }

  void _validateId(String value) {
    if (!RegExp(r'^[A-Za-z0-9_-]{1,128}$').hasMatch(value)) {
      throw ArgumentError.value(value.length, 'userId', 'Invalid identifier.');
    }
  }
}
