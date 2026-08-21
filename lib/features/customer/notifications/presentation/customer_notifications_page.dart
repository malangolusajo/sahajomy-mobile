import 'package:flutter/material.dart';

import '../data/customer_notifications_repository.dart';

class CustomerNotificationsPage extends StatefulWidget {
  const CustomerNotificationsPage({super.key});

  @override
  State<CustomerNotificationsPage> createState() =>
      _CustomerNotificationsPageState();
}

class _CustomerNotificationsPageState extends State<CustomerNotificationsPage> {
  final _repository = CustomerNotificationsRepository();
  late Future<List<Map<String, dynamic>>> _notifications = _repository
      .listNotifications();
  var _isMarkingAllRead = false;

  void _reload() =>
      setState(() => _notifications = _repository.listNotifications());

  Future<void> _markRead(Map<String, dynamic> notification) async {
    if (notification['is_read'] == true) return;
    try {
      await _repository.markRead(notification['id'] as String);
      _reload();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Unable to update this notification.')),
        );
      }
    }
  }

  Future<void> _markAllRead() async {
    setState(() => _isMarkingAllRead = true);
    try {
      await _repository.markAllRead();
      _reload();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Unable to mark notifications as read.'),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isMarkingAllRead = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('Notifications'),
      actions: [
        TextButton(
          onPressed: _isMarkingAllRead ? null : _markAllRead,
          child: const Text('Mark all read'),
        ),
      ],
    ),
    body: FutureBuilder<List<Map<String, dynamic>>>(
      future: _notifications,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return Center(
            child: OutlinedButton(
              onPressed: _reload,
              child: const Text('Try again'),
            ),
          );
        }
        final notifications = snapshot.data ?? [];
        if (notifications.isEmpty) {
          return const Center(child: Text('You have no notifications yet.'));
        }
        return ListView.separated(
          padding: const EdgeInsets.all(20),
          itemCount: notifications.length,
          separatorBuilder: (_, _) => const SizedBox(height: 10),
          itemBuilder: (_, index) => _NotificationCard(
            notification: notifications[index],
            onTap: () => _markRead(notifications[index]),
          ),
        );
      },
    ),
  );
}

class _NotificationCard extends StatelessWidget {
  const _NotificationCard({required this.notification, required this.onTap});

  final Map<String, dynamic> notification;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final isRead = notification['is_read'] == true;
    final priority = notification['priority'] as String? ?? 'info';
    return Card(
      color: isRead ? null : Theme.of(context).colorScheme.primaryContainer,
      child: ListTile(
        contentPadding: const EdgeInsets.all(16),
        leading: Icon(
          priority == 'warning'
              ? Icons.warning_amber_rounded
              : Icons.info_outline,
        ),
        title: Text(
          notification['type'] as String? ?? 'Sahajomy update',
          style: TextStyle(
            fontWeight: isRead ? FontWeight.w600 : FontWeight.w800,
          ),
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 5),
          child: Text(notification['message'] as String? ?? ''),
        ),
        trailing: isRead ? null : const Icon(Icons.circle, size: 10),
        onTap: onTap,
      ),
    );
  }
}
