import 'package:flutter/material.dart';

import '../data/customer_air_cargo_repository.dart';

class AirCargoBookingListPage extends StatefulWidget {
  const AirCargoBookingListPage({super.key});

  @override
  State<AirCargoBookingListPage> createState() =>
      _AirCargoBookingListPageState();
}

class _AirCargoBookingListPageState extends State<AirCargoBookingListPage> {
  final _repository = CustomerAirCargoRepository();
  late Future<List<Map<String, dynamic>>> _bookings = _repository
      .listBookings();

  void _retry() => setState(() => _bookings = _repository.listBookings());

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Express air cargo')),
    body: FutureBuilder<List<Map<String, dynamic>>>(
      future: _bookings,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return _AirCargoMessage(
            message: 'We could not load your air cargo bookings.',
            actionLabel: 'Try again',
            onAction: _retry,
          );
        }
        final bookings = snapshot.data ?? [];
        if (bookings.isEmpty) {
          return const _AirCargoMessage(
            message: 'No Express Air Cargo bookings yet.',
          );
        }
        return ListView.separated(
          padding: const EdgeInsets.all(20),
          itemCount: bookings.length,
          separatorBuilder: (_, _) => const SizedBox(height: 12),
          itemBuilder: (_, index) => _AirCargoCard(booking: bookings[index]),
        );
      },
    ),
  );
}

class _AirCargoCard extends StatelessWidget {
  const _AirCargoCard({required this.booking});

  final Map<String, dynamic> booking;

  @override
  Widget build(BuildContext context) {
    final pricing = booking['pricing'] as Map?;
    final quotedTotal = pricing?['quoted_total'];
    final currency = pricing?['currency'] ?? 'TZS';
    return Card(
      child: ListTile(
        contentPadding: const EdgeInsets.all(16),
        leading: const CircleAvatar(child: Icon(Icons.flight_takeoff_outlined)),
        title: Text(
          booking['tracking_number'] as String? ?? 'Air cargo booking',
          style: const TextStyle(fontWeight: FontWeight.w800),
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Text(
            '${booking['cargo_type'] ?? 'Cargo'} | ${booking['weight_kg'] ?? 0} KG\n'
            '${booking['route'] ?? booking['destination_region'] ?? 'Route pending'}\n'
            '${booking['status'] ?? 'Pending'}${quotedTotal == null ? ' | Quote pending' : ' | $currency $quotedTotal'}',
          ),
        ),
      ),
    );
  }
}

class _AirCargoMessage extends StatelessWidget {
  const _AirCargoMessage({
    required this.message,
    this.actionLabel,
    this.onAction,
  });

  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.flight_takeoff_outlined, size: 44),
          const SizedBox(height: 14),
          Text(message, textAlign: TextAlign.center),
          if (onAction != null) ...[
            const SizedBox(height: 16),
            OutlinedButton(onPressed: onAction, child: Text(actionLabel!)),
          ],
        ],
      ),
    ),
  );
}
