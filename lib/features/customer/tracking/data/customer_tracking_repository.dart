import '../../../../core/auth/session_store.dart';
import '../../../../core/network/authenticated_api_client.dart';
import '../../../../core/network/api_client.dart';

class CustomerTrackingRepository {
  CustomerTrackingRepository({this.client, SessionStore? sessionStore})
    : _store = sessionStore ?? SessionStore();

  final ApiClient? client;
  final SessionStore _store;

  Future<List<Map<String, dynamic>>> listEvents() async {
    final api = client ?? authenticatedApiClient(_store);
    final results = await Future.wait([
      api.getList('tracking/customer/reservations'),
      api.getList('tracking/customer/bookings'),
      api.getList('tracking/customer/shipment_orders'),
    ]);
    final events = results.expand((items) => items).toList();
    events.sort((a, b) {
      final left = a['timestamp'] as String? ?? '';
      final right = b['timestamp'] as String? ?? '';
      return right.compareTo(left);
    });
    return events;
  }
}
