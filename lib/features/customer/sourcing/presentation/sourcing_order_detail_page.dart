import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../app/theme.dart';
import '../../../../features/repository_providers.dart';
import '../../presentation/customer_components.dart';

class SourcingOrderDetailPage extends ConsumerStatefulWidget {
  const SourcingOrderDetailPage({required this.orderId, super.key});

  final String orderId;

  @override
  ConsumerState<SourcingOrderDetailPage> createState() => _SourcingOrderDetailPageState();
}

class _SourcingOrderDetailPageState extends ConsumerState<SourcingOrderDetailPage> {
  late Future<Map<String, dynamic>> _order;

  @override
  void initState() {
    super.initState();
    _order = ref.read(customerSourcingRepositoryProvider).getOrder(widget.orderId);
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Sourcing order',
    body: FutureBuilder<Map<String, dynamic>>(
      future: _order,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return CustomerEmptyState(
            icon: Icons.error_outline,
            message: 'Could not load this sourcing order.',
            actionLabel: 'Retry',
            onAction: () => setState(() {
              _order = ref.read(customerSourcingRepositoryProvider).getOrder(widget.orderId);
            }),
          );
        }
        final o = snapshot.data!;
        final status = o['delivery_status'] ?? o['status'] ?? '—';
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          children: [
            CustomerHeroCard(
              eyebrow: 'Booking',
              title: 'Sourcing order',
              subtitle: '${o['id'] ?? ''} · Latest verified status',
            ),
            const SizedBox(height: 24),
            Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: appBorder),
              ),
              child: Column(
                children: [
                  _row('ST', 'Status', status.toString().replaceAll('_', ' '), brandCoral, status.toString()),
                  const Divider(height: 1, indent: 60),
                  _row('RT', 'Route', '${o['origin'] ?? 'Yiwu'} → ${o['destination'] ?? 'Dar es Salaam'}', appMuted, null),
                  const Divider(height: 1, indent: 60),
                  _row('GD', 'Cargo', '${o['goods_type'] ?? 'Goods'} · ${o['carton_count'] ?? o['items_count'] ?? 0} cartons', appMuted, null),
                  const Divider(height: 1, indent: 60),
                  _row('DC', 'Documents', 'Invoice · Receipt · Packing list', appMuted, null),
                ],
              ),
            ),
          ],
        );
      },
    ),
  );

  Widget _row(String badge, String title, String subtitle, Color badgeColor, String? tag) => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    child: Row(
      children: [
        Container(
          width: 40,
          height: 40,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: badgeColor.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Text(badge, style: TextStyle(color: badgeColor, fontWeight: FontWeight.w800)),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
              const SizedBox(height: 2),
              Text(subtitle, style: const TextStyle(color: appMuted, fontSize: 13)),
            ],
          ),
        ),
        if (tag != null) CustomerStatusPill(label: tag),
      ],
    ),
  );
}
