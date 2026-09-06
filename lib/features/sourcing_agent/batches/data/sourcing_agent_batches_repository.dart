import '../../../../core/network/api_client.dart';

class SourcingAgentBatchesRepository {
  SourcingAgentBatchesRepository({required this.client});

  final ApiClient client;

  Future<Map<String, dynamic>> listBatches() =>
      client.getObject('sourcing_agent/batches');

  Future<Map<String, dynamic>> getBatch(String batchId) =>
      client.getObject('sourcing_agent/batches/$batchId');

  Future<Map<String, dynamic>> listOrders(String batchId) =>
      client.getObject('sourcing_agent/batches/$batchId/orders');

  Future<Map<String, dynamic>> createBatch({
    required String title,
    String? description,
    required String currency,
    required String shippingMethod,
    double? shippingFeePerCbm,
  }) => client.post<Map<String, dynamic>>(
    'sourcing_agent/batches',
    data: {
      'title': title,
      'description': description,
      'currency': currency,
      'shipping_method': shippingMethod,
      'shipping_fee_per_cbm': shippingFeePerCbm,
    },
  );

  Future<Map<String, dynamic>> createPackingList({
    required String batchId,
    required String name,
    String? description,
  }) => client.post<Map<String, dynamic>>(
    'sourcing_agent/batches/$batchId/packing-lists',
    data: {'name': name, 'description': description},
  );

  Future<Map<String, dynamic>> createProduct({
    required String batchId,
    required String goodsTypeId,
    required String name,
    String? description,
    required double pricePerUnit,
    required int minimumOrderQuantity,
    required String imageUrl,
  }) => client.post<Map<String, dynamic>>(
    'sourcing_agent/batches/$batchId/products',
    data: {
      'goods_type_id': goodsTypeId,
      'name': name,
      'description': description,
      'price_per_unit': pricePerUnit,
      'minimum_order_quantity': minimumOrderQuantity,
      'image_url': imageUrl,
      'status': 'draft',
    },
  );

  Future<Map<String, dynamic>> listGoodsCategories() =>
      client.getObject('sourcing_agent/goods/categories');
}
