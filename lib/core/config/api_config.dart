class ApiConfig {
  const ApiConfig._();

  static const baseUrl = String.fromEnvironment(
    'API_URL',
    defaultValue: 'https://sahajomy.co.tz/api/v1',
  );

  static Uri uri(String path, [Map<String, String>? queryParameters]) {
    final normalizedPath = path.startsWith('/') ? path.substring(1) : path;
    return Uri.parse('$baseUrl/$normalizedPath')
        .replace(queryParameters: queryParameters);
  }
}
