import '../../../core/auth/session_store.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/authenticated_api_client.dart';

/// Provides live data for reference routes that do not need a dedicated form.
class WorkflowApiRepository {
  WorkflowApiRepository({ApiClient? client, SessionStore? sessionStore})
    : _api = client ?? authenticatedApiClient(sessionStore ?? SessionStore());

  final ApiClient _api;

  Future<Object> load(String endpoint) => _api.getObject(endpoint);

  Future<Map<String, dynamic>> submit(
    String endpoint,
    Map<String, dynamic> payload,
  ) => _api.post(endpoint, body: payload);

  Future<Map<String, dynamic>> submitForm(
    String endpoint,
    Map<String, String> fields,
  ) => _api.postForm(endpoint, fields: fields);
}
