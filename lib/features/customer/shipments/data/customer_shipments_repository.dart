import '../../../../core/auth/session_store.dart';
import '../../../../core/network/authenticated_api_client.dart';
import '../../../../core/network/api_client.dart';

class CustomerShipmentsRepository {
  CustomerShipmentsRepository({this._client, SessionStore? sessionStore})
    : _store = sessionStore ?? SessionStore();

  final SessionStore _store;
  final ApiClient? _client;

  Future<List<Map<String, dynamic>>> listShipmentOrders() {
    final client = _client ?? authenticatedApiClient(_store);
    return client.getList('customer/shipment-orders');
  }
}
