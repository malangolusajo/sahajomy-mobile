import '../../../../core/auth/session_store.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/network/authenticated_api_client.dart';

class SourcingAgentBatchesRepository {
  SourcingAgentBatchesRepository({this.client, SessionStore? sessionStore})
    : _store = sessionStore ?? SessionStore();
  final ApiClient? client;
  final SessionStore _store;
  Future<Map<String, dynamic>> listBatches() =>
      (client ?? authenticatedApiClient(_store)).get('sourcing_agent/batches');

  Future<Map<String, dynamic>> getBatch(String batchId) =>
      (client ?? authenticatedApiClient(_store)).get(
        'sourcing_agent/batches/$batchId',
      );

  Future<Map<String, dynamic>> listOrders(String batchId) =>
      (client ?? authenticatedApiClient(_store)).get(
        'sourcing_agent/batches/$batchId/orders',
      );

  Future<Map<String, dynamic>> createBatch({
    required String title,
    String? description,
    required String currency,
    required String shippingMethod,
    double? shippingFeePerCbm,
  }) => (client ?? authenticatedApiClient(_store)).post(
    'sourcing_agent/batches',
    body: {
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
  }) => (client ?? authenticatedApiClient(_store)).post(
    'sourcing_agent/batches/$batchId/packing-lists',
    body: {'name': name, 'description': description},
  );

  Future<Map<String, dynamic>> createProduct({
    required String batchId,
    required String goodsTypeId,
    required String name,
    String? description,
    required double pricePerUnit,
    required int minimumOrderQuantity,
    required String imageUrl,
  }) => (client ?? authenticatedApiClient(_store)).post(
    'sourcing_agent/batches/$batchId/products',
    body: {
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
      (client ?? authenticatedApiClient(_store)).get(
        'sourcing_agent/goods/categories',
      );
}
