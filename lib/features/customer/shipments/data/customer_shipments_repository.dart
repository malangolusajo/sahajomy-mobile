import '../../../../core/network/api_client.dart';

class CustomerShipmentsRepository {
  CustomerShipmentsRepository({required this.client});

  final ApiClient client;

  Future<List<Map<String, dynamic>>> listShipmentOrders() =>
      client.getList('customer/shipment-orders');
}
