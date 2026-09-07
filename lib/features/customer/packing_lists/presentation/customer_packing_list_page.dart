import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sahajomy_mobile/features/repository_providers.dart';

import '../../../../core/ui/sahajomy_ui.dart';
import '../../presentation/customer_components.dart';
import '../../bookings/data/customer_booking_repository.dart';

class CustomerPackingListPage extends ConsumerStatefulWidget {
  const CustomerPackingListPage({super.key});

  @override
  ConsumerState<CustomerPackingListPage> createState() =>
      _CustomerPackingListPageState();
}

class _CustomerPackingListPageState
    extends ConsumerState<CustomerPackingListPage> {
  CustomerBookingRepository get _repository =>
      ref.read(customerBookingRepositoryProvider);
  late Future<List<Map<String, dynamic>>> _bookings = Future.microtask(
    () => _repository.listBookings(),
  );

  void _retry() => setState(() => _bookings = _repository.listBookings());

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Packing list',
    body: FutureBuilder<List<Map<String, dynamic>>>(
      future: _bookings,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return CustomerEmptyState(
            icon: Icons.error_outline,
            message: 'We could not load your container packing lists.',
            actionLabel: 'Try again',
            onAction: _retry,
          );
        }
        final bookings = snapshot.data!;
        if (bookings.isEmpty) {
          return const CustomerEmptyState(
            icon: Icons.inventory_2_outlined,
            message:
                'Packing lists will appear once your shipment is prepared.',
          );
        }
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          children: [
            const CustomerHeroCard(
              eyebrow: 'Cargo',
              title: 'Container packing list',
              subtitle: 'Review the items packed into your shipment before it departs.',
            ),
            const SizedBox(height: 24),
            for (final booking in bookings) ...[
              Card(
                child: ListTile(
                  contentPadding: const EdgeInsets.all(16),
                  title: Text(
                    '${booking['container_reference'] ?? booking['container_name'] ?? 'Container'}',
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                  subtitle: Text(
                    'Booking #${booking['booking_reference'] ?? booking['sea_booking_id'] ?? booking['id']} · ${booking['cbm_booked'] ?? 0} CBM',
                  ),
                  trailing: SahajomyStatusPill(
                    label: '${booking['goods_status'] ?? 'Status unavailable'}',
                  ),
                ),
              ),
              const SizedBox(height: 12),
            ],
          ],
        );
      },
    ),
  );
}
