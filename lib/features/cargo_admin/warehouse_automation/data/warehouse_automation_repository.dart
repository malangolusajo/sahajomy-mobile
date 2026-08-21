import '../../../../core/auth/session_store.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/network/authenticated_api_client.dart';

class WarehouseAutomationRepository {
  WarehouseAutomationRepository({this.client, SessionStore? sessionStore})
    : _store = sessionStore ?? SessionStore();

  final ApiClient? client;
  final SessionStore _store;

  ApiClient get _api => client ?? authenticatedApiClient(_store);

  Future<Map<String, dynamic>> loadStatus() =>
      _api.get('cargo_admin/warehouse-automation/status');

  Future<Map<String, dynamic>> createAccessToken(String warehouseId) =>
      _api.post(
        'cargo_admin/warehouse-automation/warehouses/$warehouseId/access-token',
      );

  Future<Map<String, dynamic>> revokeAccessToken(String warehouseId) =>
      _api.delete(
        'cargo_admin/warehouse-automation/warehouses/$warehouseId/access-token',
      );

  Future<Map<String, dynamic>> matchIntake({
    required String warehouseId,
    required String scanText,
  }) => _api.post(
    'cargo_admin/warehouse-automation/intake/match',
    body: {'warehouse_id': warehouseId, 'scan_text': scanText},
  );

  Future<Map<String, dynamic>> confirmIntake(Map<String, dynamic> payload) =>
      _api.post(
        'cargo_admin/warehouse-automation/intake/confirm',
        body: payload,
      );

  Future<Map<String, dynamic>> updateCollectionReadiness({
    required String intakeId,
    required Map<String, dynamic> payload,
  }) => _api.patch(
    'cargo_admin/warehouse-automation/intakes/$intakeId/collection-readiness',
    body: payload,
  );

  Future<Map<String, dynamic>> verifyCollection({String? code, String? pin}) {
    assert((code == null) != (pin == null));
    return _api.post(
      'cargo_admin/warehouse-automation/collection/verify',
      body: _credentialPayload(code: code, pin: pin),
    );
  }

  Future<Map<String, dynamic>> confirmCollection({
    required String requestId,
    String? code,
    String? pin,
  }) {
    assert((code == null) != (pin == null));
    return _api.post(
      'cargo_admin/warehouse-automation/collection/$requestId/confirm',
      body: _credentialPayload(code: code, pin: pin),
    );
  }

  Map<String, String> _credentialPayload({String? code, String? pin}) =>
      code != null ? {'code': code} : {'pin': pin!};
}
