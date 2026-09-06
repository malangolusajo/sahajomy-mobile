import 'package:dio/dio.dart';

import '../../../../core/network/api_client.dart';

class CustomerAirCargoRepository {
  CustomerAirCargoRepository({required this.client});

  final ApiClient client;

  Future<List<Map<String, dynamic>>> listBookings() =>
      client.getList('customer/express-air-cargo/bookings');

  Future<Map<String, dynamic>> options() =>
      client.getObject('customer/express-air-cargo/options');

  Future<Map<String, dynamic>> createBooking({
    required String cargoTypeId,
    required double weightKg,
    required DateTime shipmentDate,
    required String destinationRegion,
    required int cartonCount,
    String? cargoDescription,
    bool certificationAcknowledged = false,
  }) => client.postForm<Map<String, dynamic>>(
    'customer/express-air-cargo/book',
    data: FormData.fromMap({
      'cargo_type_id': cargoTypeId,
      'weight_kg': weightKg.toString(),
      'shipment_date': shipmentDate.toUtc().toIso8601String(),
      'destination_region': destinationRegion,
      'carton_count': cartonCount.toString(),
      'item_photos': '[]',
      'certification_acknowledged': certificationAcknowledged.toString(),
      if (cargoDescription != null && cargoDescription.isNotEmpty)
        'cargo_description': cargoDescription,
    }),
  );
}
