import '../../../../core/network/api_client.dart';

class CustomerReservationsRepository {
  CustomerReservationsRepository({required this.client});

  final ApiClient client;

  Future<List<Map<String, dynamic>>> listReservations() =>
      client.getList('customer/reservations');

  Future<Map<String, dynamic>> getReservation(String reservationId) =>
      client.getObject('customer/reservations/$reservationId');

  Future<Map<String, dynamic>> createReservation({
    required String containerId,
    required double reservedCbm,
    required String destinationRegion,
    String destinationCountry = 'Tanzania',
    int? cartonCount,
  }) => client.post<Map<String, dynamic>>(
    'customer/reservations',
    data: {
      'container_id': containerId,
      'reserved_cbm': reservedCbm,
      'destination_region': destinationRegion,
      'destination_country': destinationCountry,
      'carton_count': ?cartonCount,
    },
  );
}
