import '../../../../core/auth/session_store.dart';
import '../../../../core/network/authenticated_api_client.dart';
import '../../../../core/network/api_client.dart';

class CustomerDashboardRepository {
  CustomerDashboardRepository({this.client, SessionStore? sessionStore})
    : _store = sessionStore ?? SessionStore();

  final ApiClient? client;
  final SessionStore _store;

  Future<CustomerDashboardSummary> loadSummary() async {
    final api = client ?? authenticatedApiClient(_store);
    final results = await Future.wait([
      api.getList('customer/shipment-orders'),
      api.getList('customer/reservations'),
      api.getList('customer/orders'),
    ]);
    return CustomerDashboardSummary(
      shipments: results[0].length,
      reservations: results[1].length,
      orders: results[2].length,
    );
  }
}

class CustomerDashboardSummary {
  const CustomerDashboardSummary({
    required this.shipments,
    required this.reservations,
    required this.orders,
  });

  final int shipments;
  final int reservations;
  final int orders;
}
