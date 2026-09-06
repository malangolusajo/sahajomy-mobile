import '../../../../core/network/api_client.dart';

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
}
