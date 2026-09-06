import 'package:flutter/foundation.dart';

class ApiConfig {
  const ApiConfig._();

  static const baseUrl = String.fromEnvironment(
    'API_URL',
    defaultValue: 'https://sahajomy.co.tz/api/v1',
  );

  static Uri validatedBaseUri() {
    final uri = Uri.tryParse(baseUrl);
    if (uri == null || !uri.hasAuthority) {
      throw StateError('API_URL must be an absolute URL.');
    }
    if (kReleaseMode && uri.scheme != 'https') {
      throw StateError('Release builds require an HTTPS API URL.');
    }
    if (uri.userInfo.isNotEmpty || uri.fragment.isNotEmpty) {
      throw StateError('API_URL must not contain credentials or a fragment.');
    }
    return uri;
  }

  static Uri uri(String path, [Map<String, String>? queryParameters]) {
    final normalizedPath = path.startsWith('/') ? path.substring(1) : path;
    final base = validatedBaseUri();
    final uri = Uri.parse(
      '${base.toString().replaceFirst(RegExp(r'/$'), '')}/$normalizedPath',
    ).replace(queryParameters: queryParameters);
    return uri;
  }
}
