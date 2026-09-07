import '../../../../core/network/api_client.dart';

import 'dart:typed_data';

class CargoAdminDocumentsRepository {
  CargoAdminDocumentsRepository({required this.client});

  final ApiClient client;

  Future<List<Map<String, dynamic>>> listCustomsPackingLists() =>
      client.getList('cargo_admin/customs-packing-lists');

  Future<List<Map<String, dynamic>>> listReceipts() =>
      client.getList('cargo_admin/financial/receipts');

  Future<List<Map<String, dynamic>>> listInvoices() =>
      client.getList('cargo_admin/financial/invoices');

  Future<List<Map<String, dynamic>>> listCustomers() =>
      client.getList('cargo_admin/customers');

  Future<Map<String, dynamic>> getCustomsPackingList(String id) =>
      client.getObject('cargo_admin/customs-packing-lists/$id');

  Future<Map<String, dynamic>> finalizeCustomsPackingList(String id) =>
      client.post<Map<String, dynamic>>(
        'cargo_admin/customs-packing-lists/$id/finalize',
        data: const {},
      );

  Future<Map<String, dynamic>> cancelCustomsPackingList(String id) =>
      client.post<Map<String, dynamic>>(
        'cargo_admin/customs-packing-lists/$id/cancel',
        data: const {},
      );

  Future<Uint8List> downloadCustomsPackingListPdf(String id) =>
      client.downloadBytes('cargo_admin/customs-packing-lists/$id/pdf');
}
