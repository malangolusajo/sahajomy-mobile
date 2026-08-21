import '../../../../core/auth/session_store.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/network/authenticated_api_client.dart';

class SourcingAgentBatchesRepository {
  SourcingAgentBatchesRepository({this.client, SessionStore? sessionStore})
    : _store = sessionStore ?? SessionStore();
  final ApiClient? client;
  final SessionStore _store;
  Future<Map<String, dynamic>> listBatches() =>
      (client ?? authenticatedApiClient(_store)).get('sourcing-agent/batches');
}
