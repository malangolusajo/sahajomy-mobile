import '../../../../core/auth/session_store.dart';
import '../../../../core/network/api_client.dart';

class CustomerOrdersRepository {
  CustomerOrdersRepository({this.client, SessionStore? sessionStore})
    : _store = sessionStore ?? SessionStore();

  final ApiClient? client;
  final SessionStore _store;

  Future<List<Map<String, dynamic>>> listOrders() =>
      (client ?? ApiClient(accessTokenProvider: _token)).getList(
        'customer/orders',
      );

  Future<String?> _token() async => (await _store.read())?.accessToken;
}
