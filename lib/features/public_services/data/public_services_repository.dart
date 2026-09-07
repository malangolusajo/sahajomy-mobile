import '../../../core/network/api_client.dart';

class PublicServicesRepository {
  PublicServicesRepository({required this.client});

  final ApiClient client;

  Future<List<Map<String, dynamic>>> listContainers() =>
      client.getList('public/containers', options: ApiClient.publicOptions());

  Future<List<Map<String, dynamic>>> listMarketplaceProducts() async {
    final response = await client.getObject('public/agizisha/products', options: ApiClient.publicOptions());
    return (response['products'] as List? ?? const []).whereType<Map>().map((item) => Map<String, dynamic>.from(item)).toList();
  }

  Future<List<Map<String, dynamic>>> listMarketplaceAgents() => client.getList(
    'public/agizisha/agents',
    options: ApiClient.publicOptions(),
  );

  Future<Map<String, dynamic>> getProduct(String productId) {
    _validateIdentifier(productId, 'productId');
    return client.getObject(
      'public/agizisha/products/${Uri.encodeComponent(productId)}',
      options: ApiClient.publicOptions(),
    );
  }

  Future<Map<String, dynamic>> getSharedBatch(String token) {
    _validatePublicToken(token);
    return client.getObject(
      'public/batch/${Uri.encodeComponent(token)}',
      options: ApiClient.publicOptions(),
    );
  }

  Future<Map<String, dynamic>> verifyReceipt(String token) {
    _validatePublicToken(token);
    return client.getObject(
      'public/receipt/verify/${Uri.encodeComponent(token)}',
      options: ApiClient.publicOptions(),
    );
  }

  Future<Map<String, dynamic>> requestFclQuote(Map<String, dynamic> payload) =>
      client.post<Map<String, dynamic>>(
        'fcl-quote-request',
        data: payload,
        options: ApiClient.publicOptions(),
      );

  Future<Map<String, dynamic>> placeMarketplaceOrder(
    Map<String, dynamic> payload,
  ) => client.post<Map<String, dynamic>>(
    'public/agizisha/orders',
    data: payload,
    options: ApiClient.publicOptions(),
  );

  Future<Map<String, dynamic>> registerSourcingAgent(
    Map<String, dynamic> payload,
  ) => client.post<Map<String, dynamic>>(
    'public/sourcing-agents/register',
    data: payload,
    options: ApiClient.publicOptions(),
  );

  void _validateIdentifier(String value, String name) {
    if (!RegExp(r'^[A-Za-z0-9_-]{1,128}$').hasMatch(value)) {
      throw ArgumentError.value(value.length, name, 'Invalid identifier.');
    }
  }

  void _validatePublicToken(String value) {
    if (!RegExp(r'^[A-Za-z0-9_-]{6,512}$').hasMatch(value)) {
      throw ArgumentError.value(value.length, 'token', 'Invalid token.');
    }
  }
}
