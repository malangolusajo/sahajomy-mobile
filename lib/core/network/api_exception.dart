class ApiException implements Exception {
  const ApiException({
    required this.statusCode,
    required this.message,
    this.details,
  });

  final int statusCode;
  final String message;
  final Object? details;

  bool get isUnauthorized => statusCode == 401;
  bool get isRateLimited => statusCode == 429;
}
