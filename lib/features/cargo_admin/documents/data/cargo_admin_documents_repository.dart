import '../../../../core/auth/session_store.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/network/authenticated_api_client.dart';

class CargoAdminDocumentsRepository {
  CargoAdminDocumentsRepository({this.client, SessionStore? sessionStore})
    : _store = sessionStore ?? SessionStore();

  final ApiClient? client;
  final SessionStore _store;

  ApiClient get _api => client ?? authenticatedApiClient(_store);

  Future<List<Map<String, dynamic>>> listCustomsPackingLists() =>
      _api.getList('cargo_admin/customs-packing-lists');

  Future<List<Map<String, dynamic>>> listReceipts() =>
      _api.getList('cargo_admin/financial/receipts');

  Future<List<Map<String, dynamic>>> listInvoices() =>
      _api.getList('cargo_admin/financial/invoices');

  Future<List<Map<String, dynamic>>> listCustomers() =>
      _api.getList('cargo_admin/customers');
}
