import '../../../../core/auth/session_store.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/network/authenticated_api_client.dart';

class SuperAdminUsersRepository {
  SuperAdminUsersRepository({this.client, SessionStore? sessionStore})
    : _store = sessionStore ?? SessionStore();
  final ApiClient? client;
  final SessionStore _store;
  Future<Map<String, dynamic>> listUsers() =>
      (client ?? authenticatedApiClient(_store)).get('super-admin/users');
}
