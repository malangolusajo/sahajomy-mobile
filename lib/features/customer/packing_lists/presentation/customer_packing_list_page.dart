import 'package:flutter/material.dart';

import '../../../../core/ui/sahajomy_ui.dart';
import '../../reservations/data/customer_reservations_repository.dart';

class CustomerPackingListPage extends StatefulWidget {
  const CustomerPackingListPage({super.key});

  @override
  State<CustomerPackingListPage> createState() =>
      _CustomerPackingListPageState();
}

class _CustomerPackingListPageState extends State<CustomerPackingListPage> {
  final _repository = CustomerReservationsRepository();
  late Future<List<Map<String, dynamic>>> _reservations = _repository
      .listReservations();

  void _retry() =>
      setState(() => _reservations = _repository.listReservations());

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(role: 'Customer', title: 'Packing list'),
    body: FutureBuilder<List<Map<String, dynamic>>>(
      future: _reservations,
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
        final reservations = snapshot.data!;
        if (reservations.isEmpty) {
          return const SahajomyMessageState(
            icon: Icons.inventory_2_outlined,
            message:
                'Packing lists will appear once your shipment is prepared.',
          );
        }
        return ListView.separated(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
          itemCount: reservations.length + 1,
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
            final reservation = reservations[index - 1];
            return Card(
              child: ListTile(
                contentPadding: const EdgeInsets.all(16),
                title: Text(
                  '${reservation['container_reference'] ?? reservation['container_name'] ?? 'Container'}',
                  style: const TextStyle(fontWeight: FontWeight.w800),
                ),
                subtitle: Text(
                  'Reservation #${reservation['reservation_number'] ?? reservation['id']} · ${reservation['reserved_cbm'] ?? reservation['cbm_reserved'] ?? 0} CBM',
                ),
                trailing: SahajomyStatusPill(
                  label: '${reservation['status'] ?? 'Ready'}',
                ),
              ),
            );
          },
        );
      },
    ),
  );
}
