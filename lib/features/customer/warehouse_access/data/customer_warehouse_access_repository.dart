import '../../../../core/network/api_client.dart';

class CustomerWarehouseAccessRepository {
  CustomerWarehouseAccessRepository({required this.client});

  final ApiClient client;

  Future<Map<String, dynamic>> loadParcels(String opaqueToken) =>
      client.getObject('customer/warehouse-access/$opaqueToken');

  Future<Map<String, dynamic>> createCollectionRequest({
    required String opaqueToken,
    required List<String> intakeIds,
  }) => client.post<Map<String, dynamic>>(
    'customer/warehouse-access/$opaqueToken/collection-requests',
    data: {'intake_ids': intakeIds},
  );
}
