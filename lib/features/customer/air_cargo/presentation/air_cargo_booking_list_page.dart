import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sahajomy_mobile/features/repository_providers.dart';

import '../../presentation/customer_components.dart';
import '../data/customer_air_cargo_repository.dart';
import 'create_air_cargo_booking_page.dart';

class AirCargoBookingListPage extends ConsumerStatefulWidget {
  const AirCargoBookingListPage({super.key});

  @override
  ConsumerState<AirCargoBookingListPage> createState() =>
      _AirCargoBookingListPageState();
}

class _AirCargoBookingListPageState
    extends ConsumerState<AirCargoBookingListPage> {
  CustomerAirCargoRepository get _repository =>
      ref.read(customerAirCargoRepositoryProvider);
  late Future<List<Map<String, dynamic>>> _bookings = Future.microtask(
    () => _repository.listBookings(),
  );

  void _retry() => setState(() => _bookings = _repository.listBookings());

  Future<void> _openBooking() async {
    final created = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => const CreateAirCargoBookingPage()),
    );
    if (created == true) _retry();
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Express Air Cargo',
    body: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Padding(
          padding: EdgeInsets.fromLTRB(20, 12, 20, 12),
          child: CustomerHeroCard(
            eyebrow: 'Express Air Cargo',
            title: 'Air cargo bookings',
            subtitle: 'Book air cargo, upload cargo photos, and review existing bookings.',
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
          child: SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: _openBooking,
              child: const Text('Book air cargo'),
            ),
          ),
        ),
        Expanded(
          child: FutureBuilder<List<Map<String, dynamic>>>(
            future: _bookings,
            builder: (context, snapshot) {
              if (snapshot.connectionState != ConnectionState.done) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snapshot.hasError) {
                return CustomerEmptyState(
                  icon: Icons.flight_takeoff_outlined,
                  message: 'We could not load your air cargo bookings.',
                  actionLabel: 'Try again',
                  onAction: _retry,
                );
              }
              final bookings = snapshot.data ?? [];
              if (bookings.isEmpty) {
                return const CustomerEmptyState(
                  icon: Icons.flight_takeoff_outlined,
                  message: 'No Express Air Cargo bookings yet.',
                );
              }
              return ListView.separated(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
                itemCount: bookings.length,
                separatorBuilder: (_, _) => const SizedBox(height: 12),
                itemBuilder: (_, index) =>
                    _AirCargoCard(booking: bookings[index]),
              );
            },
          ),
        ),
      ],
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

