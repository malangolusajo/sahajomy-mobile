import '../../../../core/network/api_client.dart';

class CustomerNotificationsRepository {
  CustomerNotificationsRepository({required this.client});

  final ApiClient client;

  Future<List<Map<String, dynamic>>> listNotifications() =>
      client.getList('customer/notifications');

  Future<void> markRead(String notificationId) =>
      client.put('customer/notifications/$notificationId/mark-read');

  Future<void> markAllRead() =>
      client.put('customer/notifications/mark-all-read');

  Future<void> deleteNotification(String notificationId) =>
      client.delete('notifications/$notificationId');
}
