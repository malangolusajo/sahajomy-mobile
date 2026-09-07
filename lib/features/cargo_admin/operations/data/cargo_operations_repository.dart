import 'dart:typed_data';

import '../../../../core/network/api_client.dart';

class CargoOperationsRepository {
  CargoOperationsRepository({required this.client});

  final ApiClient client;

  // ── Dashboard ──────────────────────────────────────────
  Future<Map<String, dynamic>> dashboard() =>
      client.getObject('cargo_admin/dashboard');

  Future<List<Map<String, dynamic>>> activityFeed() =>
      client.getList('cargo_admin/activity-feed');

  Future<List<Map<String, dynamic>>> notifications() =>
      client.getList('cargo_admin/notifications');

  // ── Sea bookings (backend term; UI labels them 'Bookings') ──
  Future<List<Map<String, dynamic>>> listSeaBookings({
    String? status,
    String? containerId,
  }) async {
    final params = <String, String>{};
    if (status != null) params['status'] = status;
    if (containerId != null) params['container_id'] = containerId;
    return client.getList('cargo_admin/sea-bookings', queryParameters: params);
  }

  Future<Map<String, dynamic>> getSeaBooking(String id) async {
    final res = await client.getObject(
      'cargo_admin/sea-bookings',
      queryParameters: {'search': id},
    );
    final list = (res['sea_bookings'] as List<dynamic>? ?? [])
        .cast<Map<String, dynamic>>();
    return list.firstWhere(
      (b) => b['id'] == id,
      orElse: () => list.isNotEmpty ? list.first : <String, dynamic>{},
    );
  }

  Future<Map<String, dynamic>> updateSeaBookingStatus(
    String id, {
    required String goodsStatus,
    String? reason,
  }) => client.patch<Map<String, dynamic>>(
    'cargo_admin/sea-bookings/$id/status',
    data: {'goods_status': goodsStatus, 'reason': ?reason},
  );

  Future<Map<String, dynamic>> holdGoods(String id, {required String reason}) =>
      client.post<Map<String, dynamic>>(
        'cargo_admin/sea-bookings/$id/hold',
        data: {'hold_reason': reason},
      );

  Future<Map<String, dynamic>> releaseGoods(String id, {String? reason}) =>
      client.post<Map<String, dynamic>>(
        'cargo_admin/sea-bookings/$id/release',
        data: {'reason': ?reason},
      );

  Future<Map<String, dynamic>> collectGoods(String id, {String? reason}) =>
      client.post<Map<String, dynamic>>(
        'cargo_admin/sea-bookings/$id/collect',
        data: {'reason': ?reason},
      );

  Future<Map<String, dynamic>> confirmPayment(String id, {String? reason}) =>
      client.post<Map<String, dynamic>>(
        'cargo_admin/sea-bookings/$id/confirm-payment',
        data: {'reason': ?reason},
      );

  // ── Warehouses ─────────────────────────────────────────
  Future<List<Map<String, dynamic>>> listWarehouses() =>
      client.getList('cargo_admin/warehouses');

  Future<Map<String, dynamic>> getWarehouse(String id) =>
      client.getObject('cargo_admin/warehouses/$id');

  Future<Map<String, dynamic>> createWarehouse(Map<String, dynamic> data) =>
      client.post<Map<String, dynamic>>('cargo_admin/warehouses', data: data);

  Future<Map<String, dynamic>> updateWarehouse(
    String id,
    Map<String, dynamic> data,
  ) => client.patch<Map<String, dynamic>>(
    'cargo_admin/warehouses/$id',
    data: data,
  );

  // ── Containers ─────────────────────────────────────────
  Future<List<Map<String, dynamic>>> listContainers({
    String? status,
    String? warehouseId,
    bool includeArchived = false,
  }) {
    final params = <String, String>{
      'include_archived': includeArchived.toString(),
    };
    if (status != null) params['status'] = status;
    if (warehouseId != null) params['warehouse_id'] = warehouseId;
    return client.getList('cargo_admin/containers', queryParameters: params);
  }

  Future<Map<String, dynamic>> createContainer(Map<String, dynamic> data) =>
      client.post<Map<String, dynamic>>('cargo_admin/containers', data: data);

  Future<Map<String, dynamic>> updateContainerStatus(
    String id, {
    required String status,
    String? reason,
  }) => client.patch<Map<String, dynamic>>(
    'cargo_admin/containers/$id/status',
    data: {'status': status, 'reason': ?reason},
  );

  Future<Map<String, dynamic>> updateContainerSchedule(
    String id, {
    DateTime? departureDate,
    DateTime? estimatedArrivalDate,
  }) => client.patch<Map<String, dynamic>>(
    'cargo_admin/containers/$id/schedule',
    data: {
      if (departureDate != null)
        'departure_date': departureDate.toIso8601String(),
      if (estimatedArrivalDate != null)
        'estimated_arrival_date': estimatedArrivalDate.toIso8601String(),
    },
  );

  Future<List<Map<String, dynamic>>> containerSeaBookings(String id) =>
      client.getList('cargo_admin/containers/$id/sea-bookings');

  Future<Map<String, dynamic>> departContainer(String id) =>
      client.post<Map<String, dynamic>>(
        'cargo_admin/containers/$id/depart',
        data: {},
      );

  Future<Map<String, dynamic>> arriveContainer(String id) =>
      client.post<Map<String, dynamic>>(
        'cargo_admin/containers/$id/arrive',
        data: {},
      );

  // ── Financial: invoices / receipts ─────────────────────
  Future<List<Map<String, dynamic>>> listInvoices() =>
      client.getList('cargo_admin/financial/invoices');

  Future<List<Map<String, dynamic>>> listReceipts() =>
      client.getList('cargo_admin/financial/receipts');

  Future<List<Map<String, dynamic>>> listPackingLists() =>
      client.getList('cargo_admin/financial/packing-lists');

  Future<Map<String, dynamic>> getPackingList(String id) =>
      client.getObject('cargo_admin/financial/packing-lists/$id');

  Future<Map<String, dynamic>> getConsolidatedPackingList(String containerId) =>
      client.getObject(
        'cargo_admin/containers/$containerId/consolidated-packing-list',
      );

  Future<Uint8List> exportConsolidatedPackingListPdf(
    String containerId,
  ) => client.downloadBytes(
    'cargo_admin/containers/$containerId/consolidated-packing-list/export/pdf',
  );

  Future<Map<String, dynamic>> generateInvoice(
    String seaBookingId, {
    String? notes,
    DateTime? dueDate,
    String format = 'both',
    bool sendToCustomer = true,
  }) => client.post<Map<String, dynamic>>(
    'cargo_admin/sea-bookings/$seaBookingId/generate-invoice',
    queryParameters: {'format': format},
    data: const {},
  );

  Future<Map<String, dynamic>> generateReceipt(
    String seaBookingId, {
    String? notes,
    String? paymentReference,
  }) => client.post<Map<String, dynamic>>(
    'cargo_admin/sea-bookings/$seaBookingId/generate-receipt',
    queryParameters: const {'format': 'both'},
    data: const {},
  );

  Future<List<Map<String, dynamic>>> seaBookingInvoices(String id) =>
      client.getList('cargo_admin/sea-bookings/$id/invoices');

  Future<List<Map<String, dynamic>>> seaBookingReceipts(String id) =>
      client.getList('cargo_admin/sea-bookings/$id/receipts');

  Future<Uint8List> downloadInvoicePdf({
    required String seaBookingId,
    required String invoiceId,
  }) => client.downloadBytes(
    'cargo_admin/sea-bookings/$seaBookingId/invoices/$invoiceId/pdf',
  );

  Future<Uint8List> downloadReceiptPdf({
    required String seaBookingId,
    required String receiptId,
  }) => client.downloadBytes(
    'cargo_admin/sea-bookings/$seaBookingId/receipts/$receiptId/pdf',
  );

  // ── Air departure schedules ────────────────────────────
  Future<List<Map<String, dynamic>>> listAirSchedules() =>
      client.getList('cargo_admin/air-departure-schedules');

  Future<Map<String, dynamic>> createAirSchedule(Map<String, dynamic> data) =>
      client.post<Map<String, dynamic>>(
        'cargo_admin/air-departure-schedules',
        data: data,
      );

  Future<Map<String, dynamic>> updateAirSchedule(
    String id,
    Map<String, dynamic> data,
  ) => client.patch<Map<String, dynamic>>(
    'cargo_admin/air-departure-schedules/$id',
    data: data,
  );

  Future<List<Map<String, dynamic>>> listAirBookings() =>
      client.getList('cargo_admin/express-air-cargo/bookings');

  Future<Map<String, dynamic>> getAirBooking(String id) async {
    final list = await listAirBookings();
    return list.firstWhere(
      (b) => b['id'] == id,
      orElse: () => list.isNotEmpty ? list.first : <String, dynamic>{},
    );
  }

  Future<Map<String, dynamic>> updateAirBookingStatus(
    String id, {
    required String status,
    String? reason,
  }) => client.patch<Map<String, dynamic>>(
    'cargo_admin/express-air-cargo/$id/status',
    data: {'status': status, 'reason': ?reason},
  );
}
