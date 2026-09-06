import '../../../core/network/api_client.dart';

enum BookingAccount { customer, sourcingAgent }

class GuidedBookingRepository {
  GuidedBookingRepository({required this.client});

  final ApiClient client;

  Future<List<Map<String, dynamic>>> listSeaServices({
    required BookingAccount account,
    int page = 1,
    String? search,
  }) async {
    final endpoint = account == BookingAccount.customer
        ? 'customer/containers'
        : 'sourcing_agent/containers';
    final response = await client.get<Object>(
      endpoint,
      queryParameters: {
        'page': page,
        'page_size': 20,
        if (search != null && search.trim().isNotEmpty) 'search': search.trim(),
      },
    );
    return _records(response);
  }

  Future<Map<String, dynamic>> prepareSeaAddress({
    required String containerId,
  }) => client.post<Map<String, dynamic>>(
    'forwarding/prepare-address',
    data: {'cargo_mode': 'sea', 'container_id': containerId},
  );

  Future<Map<String, dynamic>> confirmSeaBooking({
    required BookingAccount account,
    required Map<String, dynamic> payload,
  }) {
    final endpoint = account == BookingAccount.customer
        ? 'customer/sea-bookings'
        : 'sourcing_agent/containers/reserve-cbm';
    return client.post<Map<String, dynamic>>(endpoint, data: payload);
  }

  List<Map<String, dynamic>> _records(Object response) {
    if (response is List) {
      return response.whereType<Map>().map(_map).toList(growable: false);
    }
    if (response is Map) {
      final map = _map(response);
      for (final key in const ['items', 'results', 'data', 'containers']) {
        final records = map[key];
        if (records is List) {
          return records.whereType<Map>().map(_map).toList(growable: false);
        }
      }
    }
    return const [];
  }

  Map<String, dynamic> _map(Map value) => Map<String, dynamic>.from(value);
}
