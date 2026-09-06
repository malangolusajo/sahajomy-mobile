import '../../../../core/network/api_client.dart';

class SuperAdminUsersRepository {
  SuperAdminUsersRepository({required this.client});

  final ApiClient client;

  Future<Map<String, dynamic>> listUsers() =>
      client.getObject('super_admin/users');

  Future<Map<String, dynamic>> updateStatus({
    required String userId,
    required String status,
  }) => client.patch<Map<String, dynamic>>(
    'super_admin/users/$userId/status',
    data: {'status': status},
  );

  Future<Map<String, dynamic>> updateVerification({
    required String userId,
    required bool isVerified,
  }) => client.patch<Map<String, dynamic>>(
    'super_admin/users/$userId/verification',
    data: {'is_verified': isVerified},
  );
}
