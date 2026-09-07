import '../domain/dashboard_summary.dart';
import '../../../../core/network/api_client.dart';

class CustomerDashboardRepository {
  CustomerDashboardRepository({required this.client});

  final ApiClient client;

  Future<CustomerDashboardSummary> loadSummary() async {
    final results = await Future.wait([
      client.getList('customer/shipment-orders'),
      client.getList('customer/sea-bookings'),
      client.getList('customer/orders'),
    ]);
    return CustomerDashboardSummary(
      shipments: results[0].length,
      bookings: results[1].length,
      orders: results[2].length,
    );
  }
}
