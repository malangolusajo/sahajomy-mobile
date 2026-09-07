import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../../../features/repository_providers.dart';
import '../../../customer/presentation/customer_components.dart';

class CargoReservationsPage extends ConsumerStatefulWidget {
  const CargoReservationsPage({this.containerId, super.key});
  final String? containerId;

  @override
  ConsumerState<CargoReservationsPage> createState() => _CargoReservationsPageState();
}

class _CargoReservationsPageState extends ConsumerState<CargoReservationsPage> {
  late Future<List<Map<String, dynamic>>> _reservations;

  @override
  void initState() {
    super.initState();
    _reservations = ref.read(cargoOperationsRepositoryProvider).listReservations(containerId: widget.containerId);
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'CARGO COMPANY',
    title: 'Bookings',
    notificationRoute: '/cargo/notifications',
    body: RefreshIndicator(
      onRefresh: () async {
        setState(() {
          _reservations = ref.read(cargoOperationsRepositoryProvider).listReservations(containerId: widget.containerId);
        });
        await _reservations;
      },
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          const CustomerHeroCard(eyebrow: 'Bookings', title: 'Customer bookings', subtitle: 'Review CBM bookings, goods status, and payment for each booking.'),
          const SizedBox(height: 20),
          FutureBuilder<List<Map<String, dynamic>>>(
            future: _reservations,
            builder: (context, snapshot) {
              if (snapshot.connectionState != ConnectionState.done) return const CustomerSkeletonList(count: 5);
              if (snapshot.hasError) return CustomerEmptyState(icon: Icons.error_outline, message: 'Could not load bookings.');
              final list = snapshot.data ?? [];
              if (list.isEmpty) return const CustomerEmptyState(icon: Icons.inbox_outlined, message: 'No bookings yet.');
              return Container(decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)), child: Column(children: [
                for (var i = 0; i < list.length; i++) ...[
                  _row(list[i], i + 1),
                  if (i < list.length - 1) const Divider(height: 1, indent: 60),
                ],
              ]));
            },
          ),
        ],
      ),
    ),
  );

  Widget _row(Map<String, dynamic> r, int idx) => InkWell(
    onTap: () => context.push('/cargo/reservations/${r['id']}'),
    child: Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      child: Row(children: [
        Container(width: 40, height: 40, alignment: Alignment.center, decoration: BoxDecoration(color: (idx <= 1 ? brandCoral : appMuted).withValues(alpha: 0.1), borderRadius: BorderRadius.circular(10)), child: Text('R$idx', style: TextStyle(color: idx <= 1 ? brandCoral : appMuted, fontWeight: FontWeight.w800))),
        const SizedBox(width: 14),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(r['shipping_mark'] ?? r['id'] ?? 'Booking', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
          const SizedBox(height: 2),
          Text('${r['cbm_booked'] ?? 0} CBM · ${r['goods_status'] ?? 'pending'}', style: const TextStyle(color: appMuted, fontSize: 13)),
        ])),
        CustomerStatusPill(label: (r['goods_status'] ?? r['status'] ?? 'pending').toString().replaceAll('_', ' ')),
      ]),
    ),
  );
}

class CargoReservationDetailPage extends ConsumerStatefulWidget {
  const CargoReservationDetailPage({required this.reservationId, super.key});
  final String reservationId;

  @override
  ConsumerState<CargoReservationDetailPage> createState() => _CargoReservationDetailPageState();
}

class _CargoReservationDetailPageState extends ConsumerState<CargoReservationDetailPage> {
  late Future<Map<String, dynamic>> _reservation;

  @override
  void initState() {
    super.initState();
    _reservation = ref.read(cargoOperationsRepositoryProvider).getReservation(widget.reservationId);
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'BOOKING',
    title: 'Booking detail',
    notificationRoute: '/cargo/notifications',
    body: FutureBuilder<Map<String, dynamic>>(
      future: _reservation,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
        if (snapshot.hasError) return const CustomerEmptyState(icon: Icons.error_outline, message: 'Could not load booking.');
        final r = snapshot.data ?? {};
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          children: [
            CustomerHeroCard(eyebrow: r['cargo_type'] ?? 'Sea Cargo', title: r['shipping_mark'] ?? r['id'] ?? 'Booking', subtitle: '${r['customer_display_name'] ?? 'Customer'} · ${r['cbm_booked'] ?? 0} CBM'),
            const SizedBox(height: 20),
            _panel([
              _kv('Goods status', (r['goods_status'] ?? 'pending').toString().replaceAll('_', ' ')),
              const Divider(),
              _kv('Payment status', (r['payment_status'] ?? 'pending').toString().replaceAll('_', ' ')),
              const Divider(),
              _kv('Logistics charge', '${r['currency'] ?? 'TZS'} ${r['logistics_charge'] ?? 0}'),
              const Divider(),
              _kv('CBM booked', '${r['cbm_booked'] ?? 0}'),
            ]),
            const SizedBox(height: 24),
            FilledButton.icon(onPressed: () => context.push('/cargo/reservations/${widget.reservationId}/packing-list'), icon: const Icon(Icons.list_alt), label: const Text('Packing list')),
            const SizedBox(height: 12),
            Row(children: [
              Expanded(child: OutlinedButton.icon(onPressed: () => _action('hold', reason: 'Quality check pending'), icon: const Icon(Icons.pause), label: const Text('Hold'))),
              const SizedBox(width: 10),
              Expanded(child: OutlinedButton.icon(onPressed: () => _action('release'), icon: const Icon(Icons.play_arrow), label: const Text('Release'))),
            ]),
            const SizedBox(height: 12),
            OutlinedButton.icon(onPressed: () => _action('collect'), icon: const Icon(Icons.check_circle), label: const Text('Mark collected')),
          ],
        );
      },
    ),
  );

  Widget _panel(List<Widget> children) => Container(decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)), child: Padding(padding: const EdgeInsets.all(16), child: Column(children: children)));

  Widget _kv(String label, String value) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 8),
    child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
      Text(label, style: const TextStyle(color: appMuted, fontSize: 14)),
      Text(value, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
    ]),
  );

  Future<void> _action(String action, {String? reason}) async {
    try {
      final repo = ref.read(cargoOperationsRepositoryProvider);
      if (action == 'hold') {
        await repo.holdGoods(widget.reservationId, reason: reason ?? 'Hold');
      } else if (action == 'release') {
        await repo.releaseGoods(widget.reservationId);
      } else if (action == 'collect') {
        await repo.collectGoods(widget.reservationId);
      }
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Action completed')));
        setState(() {
          _reservation = ref.read(cargoOperationsRepositoryProvider).getReservation(widget.reservationId);
        });
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    }
  }
}
