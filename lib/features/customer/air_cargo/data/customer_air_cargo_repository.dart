import '../../../../core/auth/session_store.dart';
import '../../../../core/network/authenticated_api_client.dart';
import '../../../../core/network/api_client.dart';

class CustomerAirCargoRepository {
  CustomerAirCargoRepository({this.client, SessionStore? sessionStore})
    : _store = sessionStore ?? SessionStore();

  final ApiClient? client;
  final SessionStore _store;

  Future<List<Map<String, dynamic>>> listBookings() =>
      (client ?? authenticatedApiClient(_store)).getList(
        'customer/express-air-cargo/bookings',
      );

  Future<Map<String, dynamic>> options() =>
      (client ?? authenticatedApiClient(_store)).get(
        'customer/express-air-cargo/options',
      );

  Future<Map<String, dynamic>> createBooking({
    required String cargoTypeId,
    required double weightKg,
    required DateTime shipmentDate,
    required String destinationRegion,
    required int cartonCount,
    String? cargoDescription,
    bool certificationAcknowledged = false,
  }) => (client ?? authenticatedApiClient(_store)).postForm(
    'customer/express-air-cargo/book',
    fields: {
      'cargo_type_id': cargoTypeId,
      'weight_kg': weightKg.toString(),
      'shipment_date': shipmentDate.toUtc().toIso8601String(),
      'destination_region': destinationRegion,
      'carton_count': cartonCount.toString(),
      'item_photos': '[]',
      'certification_acknowledged': certificationAcknowledged.toString(),
      if (cargoDescription != null && cargoDescription.isNotEmpty)
        'cargo_description': cargoDescription,
    },
  );
}
