import 'package:dio/dio.dart';
import 'package:logger/logger.dart';

class LoggingInterceptor extends Interceptor {
  LoggingInterceptor(this._logger);

  final Logger _logger;

  static const _redactedKeys = {
    'access_token',
    'refresh_token',
    'otp_code',
    'pin',
    'password',
    'secret',
    'code',
    'token',
    'opaque_token',
    'phone',
    'phone_number',
    'email',
    'scan_text',
    'item_photos',
    'authorization',
    'x-sahajomy-company',
    'x-sahajomy-branch',
  };

  Map<String, dynamic> _redactHeaders(Map<String, dynamic> headers) {
    final result = <String, dynamic>{};
    headers.forEach((key, value) {
      result[key] = _redactedKeys.contains(key.toLowerCase())
          ? '***REDACTED***'
          : value;
    });
    return result;
  }

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    _logger.d('REQUEST[${options.method}] ${redactUriForLogging(options.uri)}');
    _logger.d('Headers: ${_redactHeaders(options.headers)}');
    if (options.data is Map<String, dynamic>) {
      _logger.d(
        'Body fields: ${(options.data as Map<String, dynamic>).keys.toList()}',
      );
    } else if (options.data is FormData) {
      final form = options.data as FormData;
      _logger.d(
        'Multipart fields: ${form.fields.map((field) => field.key).toList()}, files: ${form.files.length}',
      );
    }
    handler.next(options);
  }

  @override
  void onResponse(Response response, ResponseInterceptorHandler handler) {
    _logger.d(
      'RESPONSE[${response.statusCode}] ${redactUriForLogging(response.requestOptions.uri)}',
    );
    handler.next(response);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    _logger.e(
      'ERROR[${err.response?.statusCode ?? 'NO_RESPONSE'}] ${redactUriForLogging(err.requestOptions.uri)}',
    );
    _logger.e('Network request failed; sensitive exception details omitted.');
    handler.next(err);
  }
}

/// Returns a query-free path with capability tokens and identifiers removed.
/// This function is public so the redaction contract can be regression-tested.
String redactUriForLogging(Uri uri) {
  var path = uri.path;
  for (final marker in const [
    '/warehouse-access/',
    '/receipt/verify/',
    '/verify-receipt/',
    '/shared/',
    '/public/batch/',
    '/label/air/',
    '/label/sea/',
    '/product/',
  ]) {
    final index = path.indexOf(marker);
    if (index >= 0) {
      path = '${path.substring(0, index + marker.length)}<redacted>';
      break;
    }
  }
  return path;
}
