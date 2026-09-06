import '../../../../core/network/api_client.dart';

class CustomerOrdersRepository {
  CustomerOrdersRepository({required this.client});

  final ApiClient client;

  Future<List<Map<String, dynamic>>> listOrders() =>
      client.getList('customer/orders');
}
