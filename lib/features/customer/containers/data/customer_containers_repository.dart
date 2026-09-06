import '../../../../core/network/api_client.dart';

class CustomerContainersRepository {
  CustomerContainersRepository({required this.client});

  final ApiClient client;

  Future<List<Map<String, dynamic>>> listContainers() =>
      client.getList('customer/containers');
}
