import '../../../../core/auth/session_store.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/network/authenticated_api_client.dart';

class CustomerNotificationsRepository {
  CustomerNotificationsRepository({this.client, SessionStore? sessionStore})
    : _store = sessionStore ?? SessionStore();

  final ApiClient? client;
  final SessionStore _store;

  ApiClient get _api => client ?? authenticatedApiClient(_store);

  Future<List<Map<String, dynamic>>> listNotifications() =>
      _api.getList('customer/notifications');

  Future<void> markRead(String notificationId) =>
      _api.put('customer/notifications/$notificationId/mark-read');

  Future<void> markAllRead() =>
      _api.put('customer/notifications/mark-all-read');
}
