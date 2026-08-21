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
          return ListView(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
            children: [
              Text(
                'My reservations',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 6),
              const Text(
                'Review active and historical container-space reservations.',
              ),
              const SizedBox(height: 20),
              Card(
                child: Column(
                  children: [
                    for (var index = 0; index < items.length; index++) ...[
                      _ReservationItem(item: items[index], index: index),
                      if (index != items.length - 1) const Divider(height: 1),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 18),
              FilledButton(
                onPressed: () =>
                    Navigator.pushNamed(context, '/customer/containers'),
                child: const Text('Find container space'),
              ),
            ],
          );
        },
      );
}

class _ReservationItem extends StatelessWidget {
  const _ReservationItem({required this.item, required this.index});
  final Map<String, dynamic> item;
  final int index;

  @override
  Widget build(BuildContext context) {
    final reference = item['reservation_number'] ?? item['id'] ?? 'Reservation';
    final status = item['status'] ?? 'Pending';
    return ListTile(
      leading: CircleAvatar(
        radius: 15,
        backgroundColor: const Color(0xFFFFEEE9),
        child: Text(
          '${index + 1}',
          style: const TextStyle(
            color: Color(0xFFE85A3A),
            fontWeight: FontWeight.w800,
          ),
        ),
      ),
      title: Text(
        '$reference',
        style: const TextStyle(fontWeight: FontWeight.w800),
      ),
      subtitle: Text('$status'),
      trailing: const Icon(Icons.chevron_right),
      onTap: () => Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) =>
              ReservationDetailPage(reservationId: item['id'] as String),
        ),
      ),
    );
  }
}
