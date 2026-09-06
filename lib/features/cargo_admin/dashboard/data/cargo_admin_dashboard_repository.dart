import '../../../../core/network/api_client.dart';

class CargoAdminDashboardRepository {
  CargoAdminDashboardRepository({required this.client});

  final ApiClient client;

  Future<Map<String, dynamic>> loadDashboard() =>
      client.getObject('cargo_admin/dashboard');
}
