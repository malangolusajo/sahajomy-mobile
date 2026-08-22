import '../../../../core/auth/session_store.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/network/authenticated_api_client.dart';

class SuperAdminUsersRepository {
  SuperAdminUsersRepository({this.client, SessionStore? sessionStore})
    : _store = sessionStore ?? SessionStore();
  final ApiClient? client;
  final SessionStore _store;
  Future<Map<String, dynamic>> listUsers() =>
      (client ?? authenticatedApiClient(_store)).get('super_admin/users');

  Future<Map<String, dynamic>> updateStatus({
    required String userId,
    required String status,
  }) => (client ?? authenticatedApiClient(_store)).patch(
    'super_admin/users/$userId/status',
    body: {'status': status},
  );

  Future<Map<String, dynamic>> updateVerification({
    required String userId,
    required bool isVerified,
  }) => (client ?? authenticatedApiClient(_store)).patch(
    'super_admin/users/$userId/verification',
    body: {'is_verified': isVerified},
  );
}
