import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../../../core/ui/logistics_ui.dart';
import '../../../../core/ui/sahajomy_ui.dart';
import '../../../repository_providers.dart';
import '../../presentation/customer_components.dart';

class CustomerTrackingPage extends ConsumerStatefulWidget {
  const CustomerTrackingPage({super.key});

  @override
  ConsumerState<CustomerTrackingPage> createState() => _CustomerTrackingPageState();
}

class _CustomerTrackingPageState extends ConsumerState<CustomerTrackingPage> {
  late Future<List<Map<String, dynamic>>> _shipments;

  @override
  void initState() {
    super.initState();
    _shipments = _load();
  }

  Future<List<Map<String, dynamic>>> _load() =>
      ref.read(customerShipmentsRepositoryProvider).listShipmentOrders();

  Future<void> _refresh() async {
    final next = _load();
    setState(() => _shipments = next);
    try {
      await next;
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Tracking',
    showBack: false,
    body: RefreshIndicator(
      onRefresh: _refresh,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
        children: [
          const CustomerHeroCard(
            eyebrow: 'Shipment visibility',
            title: 'Track your shipments',
            subtitle: 'See the latest verified status and what happens next.',
          ),
          const SizedBox(height: 28),
          FutureBuilder<List<Map<String, dynamic>>>(
            future: _shipments,
            builder: (context, snapshot) {
              if (snapshot.connectionState != ConnectionState.done) {
                return const CustomerSkeletonList();
              }
              if (snapshot.hasError) {
                return SahajomyMessageState(
                  icon: Icons.cloud_off_outlined,
                  message: logisticsError(snapshot.error, 'tracking'),
                  actionLabel: 'Reload',
                  onAction: _refresh,
                );
              }
              final items = snapshot.data ?? [];
              if (items.isEmpty) {
                return const CustomerEmptyState(
                  icon: Icons.track_changes_outlined,
                  message: 'No shipments to track yet. Book cargo to see live tracking here.',
                  actionLabel: 'Book shipment',
                );
              }
              return Column(
                children: [
                  for (final item in items)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: _TrackingRow(item: item),
                    ),
                ],
              );
            },
          ),
        ],
      ),
    ),
  );
}

class _TrackingRow extends StatelessWidget {
  const _TrackingRow({required this.item});

  final Map<String, dynamic> item;

  @override
  Widget build(BuildContext context) {
    final ref = item['tracking_number'] ?? item['booking_reference'] ?? 'Shipment';
    final status = item['status'] ?? item['delivery_status'] ?? 'Processing';
    final origin = item['origin'] ?? item['container']?['origin'] ?? '';
    final dest = item['destination'] ?? item['container']?['destination'] ?? '';
    final route = (origin.toString().isNotEmpty && dest.toString().isNotEmpty)
        ? '$origin → $dest'
        : (item['route'] ?? 'Route pending');
    final latest = item['latest_update'] ?? item['current_location'] ?? '';
    final mode = item['cargo_mode'] ?? item['service_type'] ?? '';
    final badge = mode == 'air' || mode == 'Air cargo' ? 'A2' : 'S1';
    final badgeColor = mode == 'air' || mode == 'Air cargo' ? brandNavy : brandCoral;

    return CustomerListItem(
      badgeLabel: badge,
      badgeColor: badgeColor,
      title: '$ref',
      subtitle: latest.toString().isNotEmpty ? '$route · $latest' : '$route',
      status: status.toString().replaceAll('_', ' '),
      onTap: () => context.push('/customer/track-shipment/${Uri.encodeComponent('$ref')}'),
    );
  }
}
