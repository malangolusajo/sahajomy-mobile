import '../../../../core/network/api_client.dart';

import 'dart:typed_data';

class CustomerBookingRepository {
  CustomerBookingRepository({required this.client});

  final ApiClient client;

  Future<List<Map<String, dynamic>>> listContainers() =>
      client.getList('customer/containers');

  Future<List<Map<String, dynamic>>> listBookings() =>
      client.getList('customer/sea-bookings');

  Future<Map<String, dynamic>> getBooking(String bookingId) =>
      client.getObject('customer/sea-bookings/$bookingId');

  Future<Map<String, dynamic>> createBooking({
    required String containerId,
    required double bookedCbm,
    required List<String> goodsTypes,
    required String destinationRegion,
    String? destinationCountry,
    int? cartonCount,
    double? pickupLocationLat,
    double? pickupLocationLon,
  }) => client.post<Map<String, dynamic>>(
    'customer/sea-bookings',
    data: {
      'container_id': containerId,
      'booked_cbm': bookedCbm,
      'goods_types': goodsTypes,
      'destination_region': destinationRegion,
      'destination_country': ?destinationCountry,
      'carton_count': ?cartonCount,
      'pickup_location_lat': ?pickupLocationLat,
      'pickup_location_lon': ?pickupLocationLon,
    },
  );

  Future<Uint8List> downloadInvoicePdf({
    required String seaBookingId,
    required String invoiceId,
  }) => client.downloadBytes(
    'customer/sea-bookings/$seaBookingId/invoices/$invoiceId/pdf',
  );

  Future<Uint8List> downloadReceiptPdf({
    required String seaBookingId,
    required String receiptId,
  }) => client.downloadBytes(
    'customer/sea-bookings/$seaBookingId/receipts/$receiptId/pdf',
  );

  Future<Map<String, dynamic>> getShippingLabel(String seaBookingId) =>
      client.getObject('customer/sea-bookings/$seaBookingId/shipping-label');

  Future<Map<String, dynamic>> updateShippingLabel(
    String seaBookingId, {
    String? destinationRegion,
    int? cartonCount,
    String? packingListSummary,
  }) => client.patch<Map<String, dynamic>>(
    'customer/sea-bookings/$seaBookingId/shipping-label',
    data: {
      'destination_region': ?destinationRegion,
      'carton_count': ?cartonCount,
      'packing_list_summary': ?packingListSummary,
    },
  );
}
