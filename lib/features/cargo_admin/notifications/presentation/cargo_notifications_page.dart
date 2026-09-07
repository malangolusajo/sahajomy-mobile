import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../app/theme.dart';
import '../../../../features/repository_providers.dart';
import '../../../customer/presentation/customer_components.dart';

class CargoNotificationsPage extends ConsumerStatefulWidget {
  const CargoNotificationsPage({super.key});

  @override
  ConsumerState<CargoNotificationsPage> createState() => _CargoNotificationsPageState();
}

class _CargoNotificationsPageState extends ConsumerState<CargoNotificationsPage> {
  late Future<List<Map<String, dynamic>>> _notifications;

  @override
  void initState() {
    super.initState();
    _notifications = ref.read(cargoOperationsRepositoryProvider).notifications();
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'CARGO COMPANY',
    title: 'Notifications',
    notificationRoute: '/cargo/notifications',
    body: FutureBuilder<List<Map<String, dynamic>>>(
      future: _notifications,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
        final list = snapshot.data ?? [];
        if (list.isEmpty) return const CustomerEmptyState(icon: Icons.notifications_none, message: 'No notifications yet.');
        return ListView(children: [
          for (final n in list) _row(n),
        ]);
      },
    ),
  );

  Widget _row(Map<String, dynamic> n) => Container(
    margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(color: (n['read'] == true ? Colors.white : brandCoral.withValues(alpha: 0.05)), borderRadius: BorderRadius.circular(14), border: Border.all(color: appBorder)),
    child: Row(children: [
      Container(width: 40, height: 40, alignment: Alignment.center, decoration: BoxDecoration(color: brandCoral.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(10)), child: Icon(_icon(n['type']), color: brandCoral)),
      const SizedBox(width: 14),
      Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(n['title'] ?? 'Notification', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
        const SizedBox(height: 2),
        Text(n['message'] ?? '', style: const TextStyle(color: appMuted, fontSize: 12)),
      ])),
    ]),
  );

  IconData _icon(String? type) {
    switch (type) {
      case 'new_sea_booking': return Icons.receipt_long;
      case 'payment': return Icons.payments;
      case 'container': return Icons.local_shipping;
      default: return Icons.notifications;
    }
  }
}
