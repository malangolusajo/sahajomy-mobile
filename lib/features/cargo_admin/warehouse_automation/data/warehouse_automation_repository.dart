import '../../../../core/network/api_client.dart';

class WarehouseAutomationRepository {
  WarehouseAutomationRepository({required this.client});

  final ApiClient client;

  Future<Map<String, dynamic>> loadStatus() =>
      client.getObject('cargo_admin/warehouse-automation/status');

  Future<Map<String, dynamic>> createAccessToken(String warehouseId) {
    _validateId(warehouseId, 'warehouseId');
    return client.post<Map<String, dynamic>>(
      'cargo_admin/warehouse-automation/warehouses/${Uri.encodeComponent(warehouseId)}/access-token',
      data: {},
      options: ApiClient.neverReplayOptions(),
    );
  }

  Future<Map<String, dynamic>> revokeAccessToken(String warehouseId) {
    _validateId(warehouseId, 'warehouseId');
    return client.delete<Map<String, dynamic>>(
      'cargo_admin/warehouse-automation/warehouses/${Uri.encodeComponent(warehouseId)}/access-token',
      options: ApiClient.neverReplayOptions(),
    );
  }

  Future<Map<String, dynamic>> matchIntake({
    required String warehouseId,
    required String scanText,
  }) {
    _validateId(warehouseId, 'warehouseId');
    if (scanText.isEmpty ||
        scanText.length > 4096 ||
        scanText.contains(RegExp(r'[\x00-\x08\x0B\x0C\x0E-\x1F]'))) {
      throw ArgumentError.value(
        scanText.length,
        'scanText',
        'Invalid scan data.',
      );
    }
    return client.post<Map<String, dynamic>>(
      'cargo_admin/warehouse-automation/intake/match',
      data: {'warehouse_id': warehouseId, 'scan_text': scanText},
      options: ApiClient.neverReplayOptions(),
    );
  }

  Future<Map<String, dynamic>> confirmIntake(Map<String, dynamic> payload) =>
      client.post<Map<String, dynamic>>(
        'cargo_admin/warehouse-automation/intake/confirm',
        data: payload,
        options: ApiClient.neverReplayOptions(),
      );

  Future<Map<String, dynamic>> updateCollectionReadiness({
    required String intakeId,
    required Map<String, dynamic> payload,
  }) {
    _validateId(intakeId, 'intakeId');
    return client.patch<Map<String, dynamic>>(
      'cargo_admin/warehouse-automation/intakes/${Uri.encodeComponent(intakeId)}/collection-readiness',
      data: payload,
      options: ApiClient.neverReplayOptions(),
    );
  }

  Future<Map<String, dynamic>> verifyCollection({String? code, String? pin}) {
    _validateCredential(code: code, pin: pin);
    return client.post<Map<String, dynamic>>(
      'cargo_admin/warehouse-automation/collection/verify',
      data: _credentialPayload(code: code, pin: pin),
      options: ApiClient.neverReplayOptions(),
    );
  }

  Future<Map<String, dynamic>> confirmCollection({
    required String requestId,
    String? code,
    String? pin,
  }) {
    _validateId(requestId, 'requestId');
    _validateCredential(code: code, pin: pin);
    return client.post<Map<String, dynamic>>(
      'cargo_admin/warehouse-automation/collection/${Uri.encodeComponent(requestId)}/confirm',
      data: _credentialPayload(code: code, pin: pin),
      options: ApiClient.neverReplayOptions(),
    );
  }

  Map<String, String> _credentialPayload({String? code, String? pin}) =>
      code != null ? {'code': code} : {'pin': pin!};

  void _validateCredential({String? code, String? pin}) {
    if ((code == null) == (pin == null)) {
      throw ArgumentError('Exactly one collection credential is required.');
    }
    final value = code ?? pin!;
    final valid = code != null
        ? RegExp(r'^[A-Za-z0-9_-]{6,512}$').hasMatch(value)
        : RegExp(r'^[0-9]{4,10}$').hasMatch(value);
    if (!valid) throw ArgumentError('Invalid collection credential.');
  }

  void _validateId(String value, String name) {
    if (!RegExp(r'^[A-Za-z0-9_-]{1,128}$').hasMatch(value)) {
      throw ArgumentError.value(value.length, name, 'Invalid identifier.');
    }
  }
}
