import '../../../../core/auth/session_store.dart';
import '../../../../core/network/authenticated_api_client.dart';
import '../../../../core/network/api_client.dart';

class CargoAdminDashboardRepository {
  CargoAdminDashboardRepository({this.client, SessionStore? sessionStore})
    : _store = sessionStore ?? SessionStore();

  final ApiClient? client;
  final SessionStore _store;

  Future<Map<String, dynamic>> loadDashboard() =>
      (client ?? authenticatedApiClient(_store)).get('cargo_admin/dashboard');
}
