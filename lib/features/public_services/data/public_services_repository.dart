import '../../../core/network/api_client.dart';

class PublicServicesRepository {
  PublicServicesRepository({required this.client});

  final ApiClient client;

  Future<List<Map<String, dynamic>>> listContainers() =>
      client.getList('public/containers');

  Future<List<Map<String, dynamic>>> listMarketplaceProducts() =>
      client.getList('public/agizisha/products');

  Future<List<Map<String, dynamic>>> listMarketplaceAgents() =>
      client.getList('public/agizisha/agents');

  Future<Map<String, dynamic>> getProduct(String productId) =>
      client.getObject('public/agizisha/products/$productId');

  Future<Map<String, dynamic>> getSharedBatch(String token) =>
      client.getObject('public/batch/$token');

  Future<Map<String, dynamic>> verifyReceipt(String token) =>
      client.getObject('public/receipt/verify/$token');

  Future<Map<String, dynamic>> requestFclQuote(Map<String, dynamic> payload) =>
      client.post<Map<String, dynamic>>('fcl-quote-request', data: payload);

  Future<Map<String, dynamic>> placeMarketplaceOrder(
    Map<String, dynamic> payload,
  ) => client.post<Map<String, dynamic>>(
    'public/agizisha/orders',
    data: payload,
  );

  Future<Map<String, dynamic>> registerSourcingAgent(
    Map<String, dynamic> payload,
  ) => client.post<Map<String, dynamic>>(
    'public/sourcing-agents/register',
    data: payload,
  );
}
