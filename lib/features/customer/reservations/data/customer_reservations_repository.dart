import '../../../../core/auth/session_store.dart';
import '../../../../core/network/authenticated_api_client.dart';
import '../../../../core/network/api_client.dart';

class CustomerReservationsRepository {
  CustomerReservationsRepository({this.client, SessionStore? sessionStore})
    : _store = sessionStore ?? SessionStore();

  final ApiClient? client;
  final SessionStore _store;

  Future<List<Map<String, dynamic>>> listReservations() =>
      (client ?? authenticatedApiClient(_store)).getList(
        'customer/reservations',
      );

  Future<Map<String, dynamic>> getReservation(String reservationId) =>
      (client ?? authenticatedApiClient(_store)).get(
        'customer/reservations/$reservationId',
      );

  Future<Map<String, dynamic>> createReservation({
    required String containerId,
    required double reservedCbm,
    required String destinationRegion,
    String destinationCountry = 'Tanzania',
    int? cartonCount,
  }) => (client ?? authenticatedApiClient(_store)).post(
    'customer/reservations',
    body: {
      'container_id': containerId,
      'reserved_cbm': reservedCbm,
      'destination_region': destinationRegion,
      'destination_country': destinationCountry,
      'carton_count': ?cartonCount,
    },
  );
}
