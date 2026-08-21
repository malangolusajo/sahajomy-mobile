import '../../../../core/auth/session_store.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/network/authenticated_api_client.dart';

class SuperAdminWarehouseAutomationRepository {
  SuperAdminWarehouseAutomationRepository({
    this.client,
    SessionStore? sessionStore,
  }) : _store = sessionStore ?? SessionStore();

  final ApiClient? client;
  final SessionStore _store;

  ApiClient get _api => client ?? authenticatedApiClient(_store);

  Future<List<Map<String, dynamic>>> listCargoAdmins() =>
      _api.getList('super_admin/warehouse-automation/cargo-admins');

  Future<Map<String, dynamic>> setEnabled({
    required String cargoAdminId,
    required bool enabled,
  }) => _api.put(
    'super_admin/warehouse-automation/cargo-admins/$cargoAdminId',
    body: {'enabled': enabled},
  );
}
