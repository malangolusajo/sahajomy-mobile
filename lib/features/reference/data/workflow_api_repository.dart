import 'package:dio/dio.dart';

import '../../../core/network/api_client.dart';

/// Provides live data for reference routes that do not need a dedicated form.
class WorkflowApiRepository {
  WorkflowApiRepository({required this.client});

  final ApiClient client;

  Future<Object> load(String endpoint) => client.get<Object>(endpoint);

  Future<Map<String, dynamic>> submit(
    String endpoint,
    Map<String, dynamic> payload,
  ) => client.post<Map<String, dynamic>>(endpoint, data: payload);

  Future<Map<String, dynamic>> submitForm(
    String endpoint,
    Map<String, String> fields,
  ) => client.postForm<Map<String, dynamic>>(
    endpoint,
    data: FormData.fromMap(fields),
  );
}
