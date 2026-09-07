import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final notificationPermissionProvider = Provider(
  (ref) => NotificationPermission(),
);

class NotificationPermission {
  static const _channel = MethodChannel('com.sahajomy.mobile/notifications');
  Future<String> request() async {
    try {
      return await _channel.invokeMethod<String>('requestPermission') ??
          'unavailable';
    } on MissingPluginException {
      return 'unavailable';
    }
  }

  Future<void> openSettings() => _channel.invokeMethod<void>('openSettings');
}
