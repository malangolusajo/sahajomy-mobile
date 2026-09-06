import '../../../../core/network/api_client.dart';

class CustomerChinaAddressesRepository {
  CustomerChinaAddressesRepository({required this.client});

  final ApiClient client;

  Future<List<Map<String, dynamic>>> listAddresses() =>
      client.getList('customer/china-addresses');
}
