import 'package:flutter/material.dart';

import '../data/customer_reservations_repository.dart';
import 'reservation_detail_page.dart';

class ReservationListPage extends StatefulWidget {
  const ReservationListPage({super.key});
  @override
  State<ReservationListPage> createState() => _ReservationListPageState();
}

class _ReservationListPageState extends State<ReservationListPage> {
  final _repository = CustomerReservationsRepository();
  late Future<List<Map<String, dynamic>>> _reservations = _repository
      .listReservations();
  void _retry() =>
      setState(() => _reservations = _repository.listReservations());

  @override
  Widget build(BuildContext context) =>
      FutureBuilder<List<Map<String, dynamic>>>(
        future: _reservations,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(
              child: OutlinedButton(
                onPressed: _retry,
                child: const Text('Retry reservations'),
              ),
            );
          }
          final items = snapshot.data ?? [];
          if (items.isEmpty) {
            return const Center(child: Text('No reservations yet.'));
          }
          return ListView.separated(
            padding: const EdgeInsets.all(20),
            itemCount: items.length,
            separatorBuilder: (_, _) => const SizedBox(height: 10),
            itemBuilder: (_, index) {
              final item = items[index];
              final reference =
                  item['reservation_number'] ?? item['id'] ?? 'Reservation';
              final status = item['status'] ?? 'Pending';
              return Card(
                child: ListTile(
                  title: Text(
                    '$reference',
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                  subtitle: Text('$status'),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => ReservationDetailPage(
                        reservationId: item['id'] as String,
                      ),
                    ),
                  ),
                ),
              );
            },
          );
        },
      );
}
