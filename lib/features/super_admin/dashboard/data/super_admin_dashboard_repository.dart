import '../../../../core/network/api_client.dart';

class SuperAdminDashboardRepository {
  SuperAdminDashboardRepository({required this.client});

  final ApiClient client;

  Future<Map<String, dynamic>> loadOverview() =>
      client.getObject('super_admin/analytics/overview');
}
