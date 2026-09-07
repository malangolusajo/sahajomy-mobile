import '../../../../core/network/api_client.dart';

class CustomerFclQuoteRepository {
  CustomerFclQuoteRepository({required this.client});

  final ApiClient client;

  Future<Map<String, dynamic>> createQuote(Map<String, dynamic> payload) =>
      client.post<Map<String, dynamic>>('fcl-quote-request', data: payload);
}
