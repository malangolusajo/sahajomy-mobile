import '../../../../core/network/api_client.dart';
import '../../../../core/security/app_link_guard.dart';

class CustomerWarehouseAccessRepository {
  CustomerWarehouseAccessRepository({required this.client});

  final ApiClient client;

  Future<Map<String, dynamic>> loadParcels(String opaqueToken) {
    _validateToken(opaqueToken);
    return client.getObject(
      'customer/warehouse-access/${Uri.encodeComponent(opaqueToken)}',
    );
  }

  Future<Map<String, dynamic>> createCollectionRequest({
    required String opaqueToken,
    required List<String> intakeIds,
  }) {
    _validateToken(opaqueToken);
    if (intakeIds.isEmpty ||
        intakeIds.length > 100 ||
        intakeIds.any(
          (id) => !RegExp(r'^[A-Za-z0-9_-]{1,128}$').hasMatch(id),
        )) {
      throw ArgumentError.value(
        intakeIds,
        'intakeIds',
        'Invalid intake selection.',
      );
    }
    return client.post<Map<String, dynamic>>(
      'customer/warehouse-access/${Uri.encodeComponent(opaqueToken)}/collection-requests',
      data: {'intake_ids': intakeIds},
      options: ApiClient.neverReplayOptions(skipTenant: true),
    );
  }

  void _validateToken(String token) {
    if (!isValidCapabilityToken(token)) {
      throw ArgumentError.value(
        token.length,
        'opaqueToken',
        'Invalid access token.',
      );
    }
  }
}
