import 'package:flutter/material.dart';

import '../../../../core/ui/sahajomy_ui.dart';
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
    appBar: const SahajomyScreenHeader(
      role: 'Customer',
      title: 'Notifications',
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
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
          children: [
            Text(
              'Updates for you',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 6),
            const Text(
              'Important shipping, payment, and order activity appears here.',
            ),
            const SizedBox(height: 20),
            for (final notification in notifications) ...[
              _NotificationCard(
                notification: notification,
                onTap: () => _markRead(notification),
              ),
              const SizedBox(height: 12),
            ],
            const SizedBox(height: 8),
            FilledButton(
              onPressed: _isMarkingAllRead ? null : _markAllRead,
              child: const Text('Mark all as read'),
            ),
          ],
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
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      notification['type'] as String? ?? 'Sahajomy update',
                      style: TextStyle(
                        fontWeight: isRead ? FontWeight.w600 : FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      notification['message'] as String? ?? '',
                      style: const TextStyle(fontSize: 12, height: 1.5),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              SahajomyStatusPill(
                label: isRead
                    ? 'Read'
                    : priority == 'warning'
                    ? 'Action'
                    : 'New',
              ),
            ],
          ),
        ),
      ),
    );
  }
}
