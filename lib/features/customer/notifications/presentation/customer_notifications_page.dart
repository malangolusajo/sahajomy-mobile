import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:sahajomy_mobile/features/repository_providers.dart';

import '../../../../core/ui/sahajomy_ui.dart';
import '../data/customer_notifications_repository.dart';

class CustomerNotificationsPage extends ConsumerStatefulWidget {
  const CustomerNotificationsPage({super.key});

  @override
  ConsumerState<CustomerNotificationsPage> createState() =>
      _CustomerNotificationsPageState();
}

class _CustomerNotificationsPageState
    extends ConsumerState<CustomerNotificationsPage> {
  CustomerNotificationsRepository get _repository =>
      ref.read(customerNotificationsRepositoryProvider);
  late Future<List<Map<String, dynamic>>> _notifications = Future.microtask(
    () => _repository.listNotifications(),
  );
  var _isMarkingAllRead = false;

  void _reload() =>
      setState(() => _notifications = _repository.listNotifications());

  Future<void> _markRead(Map<String, dynamic> notification) async {
    try {
      if (notification['is_read'] != true) {
        await _repository.markRead(notification['id'].toString());
        _reload();
      }
      if (!mounted) return;
      final route = notification['route'] ?? notification['deep_link'];
      if (route is String && route.startsWith('/customer/')) {
        context.push(route);
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Unable to update this notification.')),
        );
      }
    }
  }

  Future<void> _delete(Map<String, dynamic> notification) async {
    try {
      await _repository.deleteNotification(notification['id'].toString());
      _reload();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Unable to delete this notification.')),
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
                onDelete: () => _delete(notification),
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
  const _NotificationCard({
    required this.notification,
    required this.onTap,
    required this.onDelete,
  });

  final Map<String, dynamic> notification;
  final VoidCallback onTap;
  final Future<void> Function() onDelete;

  @override
  Widget build(BuildContext context) {
    final isRead = notification['is_read'] == true;
    final timestamp = DateTime.tryParse(
      '${notification['created_at'] ?? notification['timestamp'] ?? ''}',
    )?.toLocal();
    final id =
        notification['id']?.toString() ?? notification.hashCode.toString();
    return Dismissible(
      key: ValueKey(id),
      direction: DismissDirection.endToStart,
      confirmDismiss: (_) => showDialog<bool>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: const Text('Delete notification?'),
          content: const Text('This notification will be removed.'),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(dialogContext, true),
              child: const Text('Delete'),
            ),
          ],
        ),
      ),
      onDismissed: (_) => onDelete(),
      background: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 28),
        color: const Color(0xFFE11D48),
        child: const Icon(Icons.delete_outline, color: Colors.white),
      ),
      child: Material(
        color: isRead ? Colors.white : const Color(0xFFFFF7F5),
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(16),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 32,
                  height: 32,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFE2DB),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(Icons.notifications_outlined, size: 18),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        notification['title'] as String? ??
                            notification['type'] as String? ??
                            'Sahajomy update',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: isRead
                              ? FontWeight.w600
                              : FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        notification['message'] as String? ?? '',
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 13, height: 20 / 13),
                      ),
                      if (timestamp != null) ...[
                        const SizedBox(height: 4),
                        Text(
                          DateFormat('MMM d, HH:mm').format(timestamp),
                          style: const TextStyle(fontSize: 11),
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                Column(
                  children: [
                    if (!isRead)
                      Container(
                        width: 6,
                        height: 6,
                        decoration: const BoxDecoration(
                          color: Color(0xFFFF6B4A),
                          shape: BoxShape.circle,
                        ),
                      ),
                    IconButton(
                      tooltip: 'Delete notification',
                      onPressed: onDelete,
                      icon: const Icon(Icons.delete_outline, size: 20),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
