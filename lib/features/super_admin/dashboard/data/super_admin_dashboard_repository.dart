import '../../../../core/auth/session_store.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/network/authenticated_api_client.dart';

class SuperAdminDashboardRepository {
  SuperAdminDashboardRepository({this.client, SessionStore? sessionStore})
    : _store = sessionStore ?? SessionStore();
  final ApiClient? client;
  final SessionStore _store;
  Future<Map<String, dynamic>> loadOverview() =>
      (client ?? authenticatedApiClient(_store)).get(
        'super-admin/analytics/overview',
      );
}
