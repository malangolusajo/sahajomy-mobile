import '../../../../core/network/api_client.dart';

class CargoAdminContainersRepository {
  CargoAdminContainersRepository({required this.client});

  final ApiClient client;

  Future<List<Map<String, dynamic>>> listContainers() =>
      client.getList('cargo_admin/containers');
}
