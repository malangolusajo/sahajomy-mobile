import '../auth/session.dart';

final RegExp _safeIdentifier = RegExp(r'^[A-Za-z0-9_-]{1,128}$');
final RegExp _capabilityToken = RegExp(r'^[A-Za-z0-9_-]{16,512}$');

String? sanitizePendingDestination(String? value, {UserRole? role}) {
  if (value == null || value.isEmpty || value.length > 1024) return null;
  final lowerValue = value.toLowerCase();
  if (value.contains('/../') ||
      value.endsWith('/..') ||
      lowerValue.contains('%2e') ||
      lowerValue.contains('%2f') ||
      lowerValue.contains('%5c') ||
      value.contains('\\')) {
    return null;
  }
  final uri = Uri.tryParse(value);
  if (uri == null ||
      uri.hasScheme ||
      uri.hasAuthority ||
      uri.fragment.isNotEmpty) {
    return null;
  }
  if (uri.path.contains('//') || uri.pathSegments.any((part) => part == '..')) {
    return null;
  }
  final path = uri.path;
  if (!_isProtectedPath(path)) return null;
  if (role != null && !_roleCanOpenPath(role, path)) return null;

  if (path.startsWith('/customer/warehouse-access/')) {
    if (uri.pathSegments.length != 3 ||
        !_capabilityToken.hasMatch(uri.pathSegments.last)) {
      return null;
    }
  }
  if (uri.queryParameters.isNotEmpty) {
    if (uri.queryParameters.length != 1 ||
        !uri.queryParameters.containsKey('container_id') ||
        !_safeIdentifier.hasMatch(uri.queryParameters['container_id'] ?? '')) {
      return null;
    }
  }
  return uri.toString();
}

bool isValidCapabilityToken(String value) => _capabilityToken.hasMatch(value);

bool _isProtectedPath(String path) =>
    path == '/customer' ||
    path.startsWith('/customer/') ||
    path == '/sourcing-agent' ||
    path.startsWith('/agent/') ||
    path == '/cargo-admin' ||
    path.startsWith('/cargo/') ||
    path == '/super-admin' ||
    path.startsWith('/admin/') ||
    path == '/account/workspaces';

bool _roleCanOpenPath(UserRole role, String path) {
  if (path == '/account/workspaces') return true;
  return switch (role) {
    UserRole.customer => path == '/customer' || path.startsWith('/customer/'),
    UserRole.sourcingAgent =>
      path == '/sourcing-agent' || path.startsWith('/agent/'),
    UserRole.cargoAdmin => path == '/cargo-admin' || path.startsWith('/cargo/'),
    UserRole.superAdmin => path == '/super-admin' || path.startsWith('/admin/'),
  };
}
