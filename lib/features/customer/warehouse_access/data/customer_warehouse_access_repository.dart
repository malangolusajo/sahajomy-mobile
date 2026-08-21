import '../../../../core/auth/session_store.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/network/authenticated_api_client.dart';

class CustomerWarehouseAccessRepository {
  CustomerWarehouseAccessRepository({this.client, SessionStore? sessionStore})
    : _store = sessionStore ?? SessionStore();

  final ApiClient? client;
  final SessionStore _store;

  ApiClient get _api => client ?? authenticatedApiClient(_store);

  Future<Map<String, dynamic>> loadParcels(String opaqueToken) =>
      _api.get('customer/warehouse-access/$opaqueToken');

  Future<Map<String, dynamic>> createCollectionRequest({
    required String opaqueToken,
    required List<String> intakeIds,
  }) => _api.post(
    'customer/warehouse-access/$opaqueToken/collection-requests',
    body: {'intake_ids': intakeIds},
  );
}
