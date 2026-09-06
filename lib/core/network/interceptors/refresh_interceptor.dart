import 'package:dio/dio.dart';

import '../api_client.dart';

class RefreshInterceptor extends Interceptor {
  RefreshInterceptor(this._apiClient);

  final ApiClient _apiClient;

  @override
  void onResponse(Response response, ResponseInterceptorHandler handler) async {
    final request = response.requestOptions;
    final shouldRefresh =
        response.statusCode == 401 &&
        request.extra['skipRefresh'] != true &&
        request.extra['refreshRetried'] != true;
    if (!shouldRefresh) {
      handler.next(response);
      return;
    }

    try {
      await _apiClient.refreshAccessTokenOnce();
      final newAccessToken = await _apiClient.tokenStorage.getAccessToken();
      if (newAccessToken != null && newAccessToken.isNotEmpty) {
        request.headers['Authorization'] = 'Bearer $newAccessToken';
        request.extra['refreshRetried'] = true;
        final retried = await _apiClient.dio.fetch(request);
        handler.resolve(retried);
        return;
      }
    } catch (_) {
      // The original 401 is mapped to an actionable ApiException downstream.
    }
    handler.next(response);
  }
}
