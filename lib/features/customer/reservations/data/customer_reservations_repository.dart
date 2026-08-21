import '../../../../core/auth/session_store.dart';
import '../../../../core/network/api_client.dart';

class CustomerReservationsRepository {
  CustomerReservationsRepository({this.client, SessionStore? sessionStore})
    : _store = sessionStore ?? SessionStore();

  final ApiClient? client;
  final SessionStore _store;

  Future<List<Map<String, dynamic>>> listReservations() =>
      (client ?? ApiClient(accessTokenProvider: _accessToken)).getList(
        'customer/reservations',
      );

  Future<Map<String, dynamic>> createReservation({
    required String containerId,
    required double reservedCbm,
    required String destinationRegion,
    String destinationCountry = 'Tanzania',
    int? cartonCount,
  }) => (client ?? ApiClient(accessTokenProvider: _accessToken)).post(
    'customer/reservations',
    body: {
      'container_id': containerId,
      'reserved_cbm': reservedCbm,
      'destination_region': destinationRegion,
      'destination_country': destinationCountry,
      'carton_count': ?cartonCount,
    },
  );

  Future<String?> _accessToken() async => (await _store.read())?.accessToken;
}
