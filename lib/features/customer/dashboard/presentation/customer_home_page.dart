import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../../../core/ui/logistics_ui.dart';
import '../../../../core/ui/sahajomy_ui.dart';
import '../../../repository_providers.dart';
import '../../presentation/customer_components.dart';

class CustomerHomePage extends ConsumerStatefulWidget {
  const CustomerHomePage({super.key});

  @override
  ConsumerState<CustomerHomePage> createState() => _CustomerHomePageState();
}

class _CustomerHomePageState extends ConsumerState<CustomerHomePage> {
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

  String _greeting() {
    final h = DateTime.now().hour;
    if (h < 12) return 'Good morning';
    if (h < 17) return 'Good afternoon';
    return 'Good evening';
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Home',
    showBack: false,
    body: RefreshIndicator(
      onRefresh: _refresh,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
        children: [
          CustomerHeroCard(
            eyebrow: _greeting(),
            title: 'Ship, source, and track',
            subtitle: 'Everything important about your China-to-Africa shipments, in one clear place.',
          ),
          const SizedBox(height: 28),
          CustomerSectionHeader(
            title: 'Active shipments',
            actionLabel: 'View all',
            onAction: () => context.push('/customer/shipments'),
          ),
          const SizedBox(height: 14),
          FutureBuilder<List<Map<String, dynamic>>>(
            future: _shipments,
            builder: (context, snapshot) {
              if (snapshot.connectionState != ConnectionState.done) {
                return const CustomerSkeletonList();
              }
              if (snapshot.hasError) {
                return SahajomyMessageState(
                  icon: Icons.cloud_off_outlined,
                  message: logisticsError(snapshot.error, 'shipments'),
                  actionLabel: 'Reload',
                  onAction: _refresh,
                );
              }
              final items = snapshot.data ?? [];
              if (items.isEmpty) {
                return const CustomerEmptyState(
                  icon: Icons.local_shipping_outlined,
                  message: 'No active shipments yet. Book your first cargo to get started.',
                  actionLabel: 'Book shipment',
                );
              }
              return Column(
                children: [
                  for (final item in items.take(3))
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: _ShipmentRow(item: item),
                    ),
                ],
              );
            },
          ),
          const SizedBox(height: 28),
          const Text(
            'Quick actions',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: appInk),
          ),
          const SizedBox(height: 18),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              CustomerQuickAction(
                label: 'Book shipment',
                icon: const Icon(Icons.add, color: Colors.white, size: 26),
                onTap: () => context.push('/customer/booking-hub'),
              ),
              CustomerQuickAction(
                label: 'Track',
                color: brandNavy,
                icon: const Icon(Icons.explore_outlined, color: Colors.white, size: 24),
                onTap: () => context.push('/customer/track-shipment'),
              ),
              CustomerQuickAction(
                label: 'China address',
                color: brandNavy,
                icon: const Text('CN', style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w800)),
                onTap: () => context.push('/customer/china-addresses'),
              ),
              CustomerQuickAction(
                label: 'Collection',
                color: brandNavy,
                icon: const Text('QR', style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w800)),
                onTap: () => context.push('/customer/collection'),
              ),
            ],
          ),
        ],
      ),
    ),
  );
}

class _ShipmentRow extends StatelessWidget {
  const _ShipmentRow({required this.item});

  final Map<String, dynamic> item;

  @override
  Widget build(BuildContext context) {
    final ref = item['tracking_number'] ?? item['booking_reference'] ?? item['order_number'] ?? 'Shipment';
    final status = item['status'] ?? item['delivery_status'] ?? item['payment_status'] ?? 'Processing';
    final origin = item['origin'] ?? item['container']?['origin'];
    final dest = item['destination'] ?? item['container']?['destination'];
    final route = (origin != null && dest != null) ? '$origin → $dest' : (item['route'] ?? 'Route pending');
    final mode = item['cargo_mode'] ?? item['service_type'] ?? '';
    final badge = mode == 'air' || mode == 'Air cargo' ? 'A2' : 'S1';
    final badgeColor = mode == 'air' || mode == 'Air cargo' ? brandNavy : brandCoral;

    return CustomerListItem(
      badgeLabel: badge,
      badgeColor: badgeColor,
      title: ref,
      subtitle: route,
      status: status.toString().replaceAll('_', ' '),
      onTap: () => context.push('/customer/shipment-orders/${Uri.encodeComponent(ref)}'),
    );
  }
}
