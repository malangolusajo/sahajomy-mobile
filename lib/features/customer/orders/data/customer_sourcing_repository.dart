import '../../../../core/network/api_client.dart';

class CustomerSourcingRepository {
  CustomerSourcingRepository({required this.client});

  final ApiClient client;

  Future<List<Map<String, dynamic>>> listOrders() =>
      client.getList('customer/orders');

  Future<Map<String, dynamic>> getOrder(String orderId) =>
      client.getObject('customer/orders/$orderId');
}
