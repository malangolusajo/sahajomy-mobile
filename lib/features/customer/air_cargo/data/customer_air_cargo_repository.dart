import 'package:dio/dio.dart';

import '../../../../core/network/api_client.dart';

class CustomerAirCargoRepository {
  CustomerAirCargoRepository({required this.client});

  final ApiClient client;

  Future<List<Map<String, dynamic>>> listBookings() =>
      client.getList('customer/express-air-cargo/bookings');

  Future<Map<String, dynamic>> options() async {
    final results = await Future.wait([
      client.getObject('customer/express-air-cargo/options'),
      client.getObject('forwarding/air-services'),
    ]);
    return {...results[0], 'services': results[1]['services'] ?? const []};
  }

  Future<Map<String, dynamic>> prepareAddress({
    required String city,
    required String country,
    required String cargoAdminId,
    required String warehouseId,
  }) => client.post<Map<String, dynamic>>(
    'forwarding/prepare-address',
    data: {
      'cargo_mode': 'air',
      'destination_city': city,
      'destination_country': country,
      'cargo_admin_id': cargoAdminId,
      'warehouse_id': warehouseId,
    },
  );

  Future<Map<String, dynamic>> createBooking({
    required String cargoTypeId,
    required double weightKg,
    required DateTime shipmentDate,
    required String destinationRegion,
    required int cartonCount,
    required String destinationCountry,
    required String cargoAdminId,
    required String warehouseId,
    required String chinaAddressId,
    String? rateId,
    String? cargoDescription,
    bool certificationAcknowledged = false,
  }) => client.postForm<Map<String, dynamic>>(
    'customer/express-air-cargo/book',
    data: FormData.fromMap({
      'cargo_type_id': cargoTypeId,
      'weight_kg': weightKg.toString(),
      'shipment_date': shipmentDate.toUtc().toIso8601String(),
      'destination_region': destinationRegion,
      'destination_country': destinationCountry,
      'cargo_admin_id': cargoAdminId,
      'warehouse_id': warehouseId,
      'customer_china_address_id': chinaAddressId,
      'air_cargo_rate_id': ?rateId,
      'carton_count': cartonCount.toString(),
      'item_photos': '[]',
      'certification_acknowledged': certificationAcknowledged.toString(),
      if (cargoDescription != null && cargoDescription.isNotEmpty)
        'cargo_description': cargoDescription,
    }),
  );
}
