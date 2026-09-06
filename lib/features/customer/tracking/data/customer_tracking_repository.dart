import '../../../../core/network/api_client.dart';

class CustomerTrackingRepository {
  CustomerTrackingRepository({required this.client});

  final ApiClient client;

  Future<List<Map<String, dynamic>>> listEvents() async {
    final results = await Future.wait([
      client.getList('tracking/customer/reservations'),
      client.getList('tracking/customer/bookings'),
      client.getList('tracking/customer/shipment_orders'),
    ]);
    final events = results.expand((items) => items).toList(growable: false);
    events.sort((a, b) {
      final left = a['timestamp'] as String? ?? '';
      final right = b['timestamp'] as String? ?? '';
      return right.compareTo(left);
    });
    return events;
  }
}
