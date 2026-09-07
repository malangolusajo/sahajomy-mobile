import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sahajomy_mobile/features/repository_providers.dart';

import '../../../../core/ui/sahajomy_ui.dart';
import '../../reservations/data/customer_booking_repository.dart';

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

  void _retry() =>
      setState(() => _bookings = _repository.listBookings());

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(role: 'Customer', title: 'Packing list'),
    body: FutureBuilder<List<Map<String, dynamic>>>(
      future: _bookings,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return SahajomyMessageState(
            icon: Icons.error_outline,
            message: 'We could not load your container packing lists.',
            actionLabel: 'Try again',
            onAction: _retry,
          );
        }
        final bookings = snapshot.data!;
        if (bookings.isEmpty) {
          return const SahajomyMessageState(
            icon: Icons.inventory_2_outlined,
            message:
                'Packing lists will appear once your shipment is prepared.',
          );
        }
        return ListView.separated(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
          itemCount: bookings.length + 1,
          separatorBuilder: (_, _) => const SizedBox(height: 12),
          itemBuilder: (context, index) {
            if (index == 0) {
              return const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Container packing list',
                    style: TextStyle(fontSize: 26, fontWeight: FontWeight.w800),
                  ),
                  SizedBox(height: 4),
                  Text(
                    'Review the items packed into your shipment before it departs.',
                  ),
                  SizedBox(height: 8),
                ],
              );
            }
            final booking = bookings[index - 1];
            return Card(
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
            );
          },
        );
      },
    ),
  );
}
