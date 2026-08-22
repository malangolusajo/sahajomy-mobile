import '../../../core/network/api_client.dart';

class PublicServicesRepository {
  PublicServicesRepository({ApiClient? client}) : _api = client ?? ApiClient();

  final ApiClient _api;

  Future<List<Map<String, dynamic>>> listContainers() =>
      _api.getList('public/containers');

  Future<List<Map<String, dynamic>>> listMarketplaceProducts() =>
      _api.getList('public/agizisha/products');

  Future<List<Map<String, dynamic>>> listMarketplaceAgents() =>
      _api.getList('public/agizisha/agents');

  Future<Map<String, dynamic>> getProduct(String productId) =>
      _api.get('public/agizisha/products/$productId');

  Future<Map<String, dynamic>> getSharedBatch(String token) =>
      _api.get('public/batch/$token');

  Future<Map<String, dynamic>> verifyReceipt(String token) =>
      _api.get('public/receipt/verify/$token');

  Future<Map<String, dynamic>> requestFclQuote(Map<String, dynamic> payload) =>
      _api.post('fcl-quote-request', body: payload);

  Future<Map<String, dynamic>> placeMarketplaceOrder(
    Map<String, dynamic> payload,
  ) => _api.post('public/agizisha/orders', body: payload);

  Future<Map<String, dynamic>> registerSourcingAgent(
    Map<String, dynamic> payload,
  ) => _api.post('public/sourcing-agents/register', body: payload);
}
