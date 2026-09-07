import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../../../features/repository_providers.dart';
import '../../../customer/presentation/customer_components.dart';

class CargoBookingDetailPage extends ConsumerStatefulWidget {
  const CargoBookingDetailPage({required this.bookingId, super.key});

  final String bookingId;

  @override
  ConsumerState<CargoBookingDetailPage> createState() => _CargoBookingDetailPageState();
}

class _CargoBookingDetailPageState extends ConsumerState<CargoBookingDetailPage> {
  late Future<Map<String, dynamic>> _booking;

  @override
  void initState() {
    super.initState();
    _booking = ref.read(cargoOperationsRepositoryProvider).getReservation(widget.bookingId);
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'CARGO COMPANY',
    title: 'Booking detail',
    notificationRoute: '/cargo/notifications',
    body: FutureBuilder<Map<String, dynamic>>(
      future: _booking,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return CustomerEmptyState(
            icon: Icons.error_outline,
            message: 'Could not load this booking.',
            actionLabel: 'Retry',
            onAction: () => setState(() {
              _booking = ref.read(cargoOperationsRepositoryProvider).getReservation(widget.bookingId);
            }),
          );
        }
        final b = snapshot.data ?? {};
        final goodsStatus = b['goods_status'] ?? 'pending';
        final paymentStatus = b['payment_status'] ?? 'pending';
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          children: [
            CustomerHeroCard(
              eyebrow: 'Sea cargo',
              title: b['reference'] ?? b['id'] ?? 'SAH-XXXX',
              subtitle: '${b['customer_name'] ?? 'Customer'} · ${b['carton_count'] ?? b['cbm_reserved'] ?? 0} ${(b['cargo_mode'] ?? 'sea') == 'air' ? 'kg' : 'cartons'}',
            ),
            const SizedBox(height: 20),
            _panel([
              _row('ST', 'Goods status', goodsStatus.toString().replaceAll('_', ' '), brandCoral),
              const Divider(height: 1, indent: 60),
              _row('PM', 'Payment status', paymentStatus.toString().replaceAll('_', ' '), appMuted),
              const Divider(height: 1, indent: 60),
              _row('CB', 'CBM booked', '${b['cbm_reserved'] ?? 0}', appMuted),
              const Divider(height: 1, indent: 60),
              _row('LC', 'Logistics charge', '${b['currency'] ?? 'TZS'} ${b['logistics_charge'] ?? 0}', appMuted),
            ]),
            const SizedBox(height: 24),
            FilledButton.icon(
              onPressed: () => context.push('/cargo/bookings/${widget.bookingId}/packing-list'),
              icon: const Icon(Icons.list_alt),
              label: const Text('Packing list'),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: goodsStatus == 'received' ? null : () => _updateStatus('received'),
                    icon: const Icon(Icons.download_done),
                    label: const Text('Mark received'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: paymentStatus == 'confirmed' ? null : () => _confirmPayment(),
                    icon: const Icon(Icons.payment),
                    label: const Text('Confirm payment'),
                  ),
                ),
              ],
            ),
          ],
        );
      },
    ),
  );

  Widget _panel(List<Widget> children) => Container(
    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)),
    child: Column(children: children),
  );

  Widget _row(String badge, String title, String subtitle, Color badgeColor) => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    child: Row(
      children: [
        Container(
          width: 40, height: 40, alignment: Alignment.center,
          decoration: BoxDecoration(color: badgeColor.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(10)),
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
      ],
    ),
  );

  Future<void> _updateStatus(String status) async {
    try {
      await ref.read(cargoOperationsRepositoryProvider).updateReservationStatus(widget.bookingId, goodsStatus: status);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Status updated')));
        setState(() {
          _booking = ref.read(cargoOperationsRepositoryProvider).getReservation(widget.bookingId);
        });
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    }
  }

  Future<void> _confirmPayment() async {
    try {
      await ref.read(cargoOperationsRepositoryProvider).confirmPayment(widget.bookingId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Payment confirmed')));
        setState(() {
          _booking = ref.read(cargoOperationsRepositoryProvider).getReservation(widget.bookingId);
        });
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    }
  }
}
