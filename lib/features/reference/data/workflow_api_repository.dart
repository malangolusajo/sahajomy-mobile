import 'package:dio/dio.dart';

import '../../../core/network/api_client.dart';

/// Provides live data for reference routes that do not need a dedicated form.
class WorkflowApiRepository {
  WorkflowApiRepository({required this.client});

  final ApiClient client;

  bool _public(String endpoint) => endpoint.startsWith('public/') || endpoint.startsWith('cargo_admin/public/') || endpoint == 'fcl-quote-request';

  Future<Object> load(String endpoint) => client.get<Object>(endpoint,
    options: _public(endpoint) ? ApiClient.publicOptions() : null);

  Future<Map<String, dynamic>> submit(
    String endpoint,
    Map<String, dynamic> payload,
  ) => client.post<Map<String, dynamic>>(endpoint, data: payload,
    options: _public(endpoint) ? ApiClient.publicOptions() : null);

  Future<Map<String, dynamic>> submitForm(
    String endpoint,
    Map<String, String> fields,
  ) => client.postForm<Map<String, dynamic>>(
    endpoint,
    data: FormData.fromMap(fields),
    options: _public(endpoint) ? ApiClient.publicOptions() : null,
  );
}
