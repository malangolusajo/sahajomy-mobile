import '../../../../core/network/api_client.dart';

class SuperAdminWarehouseAutomationRepository {
  SuperAdminWarehouseAutomationRepository({required this.client});

  final ApiClient client;

  Future<List<Map<String, dynamic>>> listCargoAdmins() =>
      client.getList('super_admin/warehouse-automation/cargo-admins');

  Future<Map<String, dynamic>> setEnabled({
    required String cargoAdminId,
    required bool enabled,
  }) => client.put<Map<String, dynamic>>(
    'super_admin/warehouse-automation/cargo-admins/$cargoAdminId',
    data: {'enabled': enabled},
  );
}
