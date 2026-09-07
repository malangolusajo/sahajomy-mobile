import '../../../../core/network/api_client.dart';

class CustomerChinaAddressesRepository {
  CustomerChinaAddressesRepository({required this.client});

  final ApiClient client;

  Future<List<Map<String, dynamic>>> listAddresses() =>
      client.getList('customer/china-addresses');

  Future<Map<String, dynamic>> getAddress(String addressId) =>
      client.getObject('customer/china-addresses/$addressId');

  Future<Map<String, dynamic>> ensureAddress({
    required String cargoMode,
    required String destinationCountry,
    required String destinationCity,
    String? containerId,
    String? airBookingId,
  }) =>
      client.post<Map<String, dynamic>>(
        'customer/china-addresses/ensure',
        data: {
          'cargo_mode': cargoMode,
          'destination_country': destinationCountry,
          'destination_city': destinationCity,
          if (containerId != null) 'container_id': containerId,
          if (airBookingId != null) 'air_booking_id': airBookingId,
        },
      );

  Future<Map<String, dynamic>> updateForwardingProfile({
    String? fullName,
    String? phone,
  }) =>
      client.patch<Map<String, dynamic>>(
        'customer/china-addresses/forwarding-profile',
        data: {
          if (fullName != null) 'full_name': fullName,
          if (phone != null) 'phone': phone,
        },
      );
}
