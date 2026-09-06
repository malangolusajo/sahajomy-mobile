import '../../../../core/network/api_client.dart';

class WarehouseAutomationRepository {
  WarehouseAutomationRepository({required this.client});

  final ApiClient client;

  Future<Map<String, dynamic>> loadStatus() =>
      client.getObject('cargo_admin/warehouse-automation/status');

  Future<Map<String, dynamic>> createAccessToken(String warehouseId) =>
      client.post<Map<String, dynamic>>(
        'cargo_admin/warehouse-automation/warehouses/$warehouseId/access-token',
        data: {},
      );

  Future<Map<String, dynamic>> revokeAccessToken(String warehouseId) =>
      client.delete<Map<String, dynamic>>(
        'cargo_admin/warehouse-automation/warehouses/$warehouseId/access-token',
      );

  Future<Map<String, dynamic>> matchIntake({
    required String warehouseId,
    required String scanText,
  }) => client.post<Map<String, dynamic>>(
    'cargo_admin/warehouse-automation/intake/match',
    data: {'warehouse_id': warehouseId, 'scan_text': scanText},
  );

  Future<Map<String, dynamic>> confirmIntake(Map<String, dynamic> payload) =>
      client.post<Map<String, dynamic>>(
        'cargo_admin/warehouse-automation/intake/confirm',
        data: payload,
      );

  Future<Map<String, dynamic>> updateCollectionReadiness({
    required String intakeId,
    required Map<String, dynamic> payload,
  }) => client.patch<Map<String, dynamic>>(
    'cargo_admin/warehouse-automation/intakes/$intakeId/collection-readiness',
    data: payload,
  );

  Future<Map<String, dynamic>> verifyCollection({String? code, String? pin}) {
    assert((code == null) != (pin == null));
    return client.post<Map<String, dynamic>>(
      'cargo_admin/warehouse-automation/collection/verify',
      data: _credentialPayload(code: code, pin: pin),
    );
  }

  Future<Map<String, dynamic>> confirmCollection({
    required String requestId,
    String? code,
    String? pin,
  }) {
    assert((code == null) != (pin == null));
    return client.post<Map<String, dynamic>>(
      'cargo_admin/warehouse-automation/collection/$requestId/confirm',
      data: _credentialPayload(code: code, pin: pin),
    );
  }

  Map<String, String> _credentialPayload({String? code, String? pin}) =>
      code != null ? {'code': code} : {'pin': pin!};
}
