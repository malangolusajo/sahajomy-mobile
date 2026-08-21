import '../../../../core/auth/session_store.dart';
import '../../../../core/network/api_client.dart';

class CustomerShipmentsRepository {
  CustomerShipmentsRepository({this._client, SessionStore? sessionStore})
    : _store = sessionStore ?? SessionStore();

  final SessionStore _store;
  final ApiClient? _client;

  Future<List<Map<String, dynamic>>> listShipmentOrders() {
    final client = _client ?? ApiClient(accessTokenProvider: _accessToken);
    return client.getList('customer/shipment-orders');
  }

  Future<String?> _accessToken() async => (await _store.read())?.accessToken;
}
