import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../../../features/repository_providers.dart';
import '../../../customer/presentation/customer_components.dart';

class CargoBookingsPage extends ConsumerStatefulWidget {
  const CargoBookingsPage({super.key});

  @override
  ConsumerState<CargoBookingsPage> createState() => _CargoBookingsPageState();
}

class _CargoBookingsPageState extends ConsumerState<CargoBookingsPage> {
  late Future<Map<String, dynamic>> _dashboard;
  late Future<List<Map<String, dynamic>>> _reservations;

  @override
  void initState() {
    super.initState();
    _dashboard = ref.read(cargoOperationsRepositoryProvider).dashboard();
    _reservations = ref.read(cargoOperationsRepositoryProvider).listReservations();
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'CARGO COMPANY',
    title: 'Cargo · Bookings',
    notificationRoute: '/cargo/notifications',
    actions: [IconButton(onPressed: () => context.push('/cargo/scanner'), icon: const Icon(Icons.qr_code_scanner))],
    body: RefreshIndicator(
      onRefresh: () async {
        setState(() {
          _dashboard = ref.read(cargoOperationsRepositoryProvider).dashboard();
          _reservations = ref.read(cargoOperationsRepositoryProvider).listReservations();
        });
        await _reservations;
      },
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          FutureBuilder<Map<String, dynamic>>(
            future: _dashboard,
            builder: (context, snapshot) {
              final data = snapshot.data ?? {};
              return CustomerHeroCard(
                eyebrow: data['branch_name'] ?? 'Main Branch',
                title: "Today's cargo operations",
                subtitle: 'Prioritize goods that need action instead of browsing a dashboard of decorative metrics.',
              );
            },
          ),
          const SizedBox(height: 16),
          FutureBuilder<List<Map<String, dynamic>>>(
            future: _reservations,
            builder: (context, snapshot) {
              if (snapshot.connectionState != ConnectionState.done) {
                return Row(
                  children: [
                    const Expanded(child: _MetricSkeleton()),
                    const SizedBox(width: 12),
                    const Expanded(child: _MetricSkeleton()),
                  ],
                );
              }
              final list = snapshot.data ?? [];
              final awaiting = list.where((r) => (r['goods_status'] ?? '') == 'ready').length;
              final readyToLoad = list.where((r) => (r['goods_status'] ?? '') == 'released').length;
              return Row(
                children: [
                  Expanded(child: _metric('Awaiting intake', '$awaiting')),
                  const SizedBox(width: 12),
                  Expanded(child: _metric('Ready to load', '$readyToLoad')),
                ],
              );
            },
          ),
          const SizedBox(height: 20),
          const CustomerSectionHeader(title: 'Recent bookings'),
          const SizedBox(height: 8),
          FutureBuilder<List<Map<String, dynamic>>>(
            future: _reservations,
            builder: (context, snapshot) {
              if (snapshot.connectionState != ConnectionState.done) {
                return const CustomerSkeletonList(count: 5);
              }
              if (snapshot.hasError) {
                return CustomerEmptyState(
                  icon: Icons.error_outline,
                  message: 'Could not load bookings.',
                  actionLabel: 'Retry',
                  onAction: () => setState(() {
                    _reservations = ref.read(cargoOperationsRepositoryProvider).listReservations();
                  }),
                );
              }
              final list = snapshot.data ?? [];
              if (list.isEmpty) {
                return const CustomerEmptyState(
                  icon: Icons.inbox_outlined,
                  message: 'No bookings yet.',
                );
              }
              return Container(
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: appBorder),
                ),
                child: Column(
                  children: [
                    for (var i = 0; i < list.length; i++) ...[
                      _bookingRow(list[i], i + 1),
                      if (i < list.length - 1) const Divider(height: 1, indent: 60),
                    ],
                  ],
                ),
              );
            },
          ),
        ],
      ),
    ),
  );

  Widget _metric(String label, String value) => Container(
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(12),
      border: Border.all(color: appBorder),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(color: appMuted, fontSize: 12)),
        const SizedBox(height: 4),
        Text(value, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
      ],
    ),
  );

  Widget _bookingRow(Map<String, dynamic> r, int idx) {
    final ref = r['shipping_mark'] ?? r['id'] ?? 'SAH-XXXX';
    final customer = r['customer_display_name'] ?? r['customer_name'] ?? r['customer']?['name'] ?? 'Customer';
    final cartons = r['carton_count'] ?? r['cbm_booked'] ?? '—';
    final mode = r['cargo_type'] ?? r['service_type'] ?? 'Sea cargo';
    final status = r['goods_status'] ?? r['status'] ?? 'pending';
    return InkWell(
      onTap: () => context.push('/cargo/bookings/${r['id']}'),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        child: Row(
          children: [
            Container(
              width: 40,
              height: 40,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: (idx <= 1 ? brandCoral : appMuted).withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text('B$idx', style: TextStyle(color: idx <= 1 ? brandCoral : appMuted, fontWeight: FontWeight.w800)),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('$ref · $customer', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
                  const SizedBox(height: 2),
                  Text('$cartons ${mode == 'air' ? 'kg' : 'cartons'} · ${mode == 'air' ? 'Air cargo' : 'Sea cargo'}', style: const TextStyle(color: appMuted, fontSize: 13)),
                ],
              ),
            ),
            CustomerStatusPill(label: status.toString().replaceAll('_', ' ')),
          ],
        ),
      ),
    );
  }
}

class _MetricSkeleton extends StatelessWidget {
  const _MetricSkeleton();

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(12),
      border: Border.all(color: appBorder),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(height: 12, width: 70, decoration: BoxDecoration(color: appBorder, borderRadius: BorderRadius.circular(6))),
        const SizedBox(height: 8),
        Container(height: 22, width: 32, decoration: BoxDecoration(color: appBorder, borderRadius: BorderRadius.circular(6))),
      ],
    ),
  );
}
