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

  // ── Reservations (bookings) ────────────────────────────
  Future<List<Map<String, dynamic>>> listReservations({
    String? status,
    String? containerId,
  }) {
    final params = <String, String>{};
    if (status != null) params['status'] = status;
    if (containerId != null) params['container_id'] = containerId;
    return client.getList('cargo_admin/reservations', queryParameters: params);
  }

  Future<Map<String, dynamic>> getReservation(String id) =>
      client.getObject('cargo_admin/reservations/$id');

  Future<Map<String, dynamic>> updateReservationStatus(
    String id, {
    required String goodsStatus,
    String? reason,
  }) =>
      client.patch<Map<String, dynamic>>(
        'cargo_admin/reservations/$id/status',
        data: {'goods_status': goodsStatus, if (reason != null) 'reason': reason},
      );

  Future<Map<String, dynamic>> holdGoods(String id, {required String reason}) =>
      client.post<Map<String, dynamic>>(
        'cargo_admin/reservations/$id/hold',
        data: {'hold_reason': reason},
      );

  Future<Map<String, dynamic>> releaseGoods(String id, {String? reason}) =>
      client.post<Map<String, dynamic>>(
        'cargo_admin/reservations/$id/release',
        data: {if (reason != null) 'reason': reason},
      );

  Future<Map<String, dynamic>> collectGoods(String id, {String? reason}) =>
      client.post<Map<String, dynamic>>(
        'cargo_admin/reservations/$id/collect',
        data: {if (reason != null) 'reason': reason},
      );

  Future<Map<String, dynamic>> confirmPayment(String id, {String? reason}) =>
      client.post<Map<String, dynamic>>(
        'cargo_admin/reservations/$id/confirm-payment',
        data: {if (reason != null) 'reason': reason},
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
  ) =>
      client.patch<Map<String, dynamic>>(
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
  }) =>
      client.patch<Map<String, dynamic>>(
        'cargo_admin/containers/$id/status',
        data: {'status': status, if (reason != null) 'reason': reason},
      );

  Future<Map<String, dynamic>> updateContainerSchedule(
    String id, {
    DateTime? departureDate,
    DateTime? estimatedArrivalDate,
  }) =>
      client.patch<Map<String, dynamic>>(
        'cargo_admin/containers/$id/schedule',
        data: {
          if (departureDate != null) 'departure_date': departureDate.toIso8601String(),
          if (estimatedArrivalDate != null)
            'estimated_arrival_date': estimatedArrivalDate.toIso8601String(),
        },
      );

  Future<List<Map<String, dynamic>>> containerReservations(String id) =>
      client.getList('cargo_admin/containers/$id/reservations');

  Future<Map<String, dynamic>> departContainer(String id) =>
      client.post<Map<String, dynamic>>('cargo_admin/containers/$id/depart', data: {});

  Future<Map<String, dynamic>> arriveContainer(String id) =>
      client.post<Map<String, dynamic>>('cargo_admin/containers/$id/arrive', data: {});

  // ── Financial: invoices / receipts ─────────────────────
  Future<List<Map<String, dynamic>>> listInvoices() =>
      client.getList('cargo_admin/financial/invoices');

  Future<List<Map<String, dynamic>>> listReceipts() =>
      client.getList('cargo_admin/financial/receipts');

  Future<List<Map<String, dynamic>>> listPackingLists() =>
      client.getList('cargo_admin/financial/packing-lists');

  Future<Map<String, dynamic>> getPackingList(String id) =>
      client.getObject('cargo_admin/financial/packing-lists/$id');

  Future<Map<String, dynamic>> generateInvoice(
    String reservationId, {
    String? notes,
    DateTime? dueDate,
    String format = 'both',
    bool sendToCustomer = true,
  }) =>
      client.post<Map<String, dynamic>>(
        'cargo_admin/reservations/$reservationId/generate-invoice',
        data: {
          if (notes != null) 'notes': notes,
          if (dueDate != null) 'due_date': dueDate.toIso8601String(),
          'format': format,
          'send_to_customer': sendToCustomer,
        },
      );

  Future<Map<String, dynamic>> generateReceipt(
    String reservationId, {
    String? notes,
    String? paymentReference,
  }) =>
      client.post<Map<String, dynamic>>(
        'cargo_admin/reservations/$reservationId/generate-receipt',
        data: {
          if (notes != null) 'notes': notes,
          if (paymentReference != null) 'payment_reference': paymentReference,
        },
      );

  Future<List<Map<String, dynamic>>> reservationInvoices(String id) =>
      client.getList('cargo_admin/reservations/$id/invoices');

  Future<List<Map<String, dynamic>>> reservationReceipts(String id) =>
      client.getList('cargo_admin/reservations/$id/receipts');

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
  ) =>
      client.patch<Map<String, dynamic>>(
        'cargo_admin/air-departure-schedules/$id',
        data: data,
      );

  Future<List<Map<String, dynamic>>> listAirBookings() =>
      client.getList('cargo_admin/express-air-cargo/bookings');

  Future<Map<String, dynamic>> getAirBooking(String id) =>
      client.getObject('cargo_admin/express-air-cargo/$id');

  Future<Map<String, dynamic>> updateAirBookingStatus(
    String id, {
    required String status,
    String? reason,
  }) =>
      client.patch<Map<String, dynamic>>(
        'cargo_admin/express-air-cargo/$id/status',
        data: {'status': status, if (reason != null) 'reason': reason},
      );
}
