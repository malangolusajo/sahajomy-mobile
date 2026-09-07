import '../../../../core/network/api_client.dart';

class CustomerContainersRepository {
  CustomerContainersRepository({required this.client});

  final ApiClient client;

  Future<List<Map<String, dynamic>>> listContainers() =>
      client.getList('customer/containers');

  Future<List<Map<String, dynamic>>> listGoodsTypes() async {
    final categories = await client.getList('public/goods/categories');
    final goodsTypes = <Map<String, dynamic>>[];
    for (final category in categories) {
      final types = category['goods_types'] as List?;
      if (types != null) {
        for (final type in types) {
          goodsTypes.add(Map<String, dynamic>.from(type as Map));
        }
      }
    }
    return goodsTypes;
  }
}