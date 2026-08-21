import '../../../../core/auth/session_store.dart';
import '../../../../core/network/authenticated_api_client.dart';
import '../../../../core/network/api_client.dart';

class CustomerContainersRepository {
  CustomerContainersRepository({this.client, SessionStore? sessionStore})
    : _store = sessionStore ?? SessionStore();
  final ApiClient? client;
  final SessionStore _store;
  Future<List<Map<String, dynamic>>> listContainers() =>
      (client ?? authenticatedApiClient(_store)).getList('customer/containers');
}
