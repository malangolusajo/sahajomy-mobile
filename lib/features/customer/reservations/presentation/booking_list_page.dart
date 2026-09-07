import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sahajomy_mobile/features/repository_providers.dart';

import '../data/customer_booking_repository.dart';
import 'booking_detail_page.dart';

class BookingListPage extends ConsumerStatefulWidget {
  const BookingListPage({super.key});
  @override
  ConsumerState<BookingListPage> createState() =>
      _BookingListPageState();
}

class _BookingListPageState extends ConsumerState<BookingListPage> {
  CustomerBookingRepository get _repository =>
      ref.read(customerBookingRepositoryProvider);
  late Future<List<Map<String, dynamic>>> _bookings = Future.microtask(
    () => _repository.listBookings(),
  );
  void _retry() =>
      setState(() => _bookings = _repository.listBookings());

  @override
  Widget build(BuildContext context) =>
      FutureBuilder<List<Map<String, dynamic>>>(
        future: _bookings,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(
              child: OutlinedButton(
                onPressed: _retry,
                child: const Text('Retry bookings'),
              ),
            );
          }
          final items = snapshot.data ?? [];
          if (items.isEmpty) {
            return Center(child: Column(mainAxisSize: MainAxisSize.min, children: [const Text('No sea freight bookings yet.'), const SizedBox(height: 16), FilledButton(onPressed: () => context.push('/customer/sea-bookings/new'), child: const Text('Book sea freight'))]));
          }
          return ListView(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
            children: [
              Text(
                'My bookings',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 6),
              const Text(
                'Review active and previous container-space bookings.',
              ),
              const SizedBox(height: 20),
              Card(
                child: Column(
                  children: [
                    for (var index = 0; index < items.length; index++) ...[
                      _BookingItem(item: items[index], index: index),
                      if (index != items.length - 1) const Divider(height: 1),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 18),
              FilledButton(
                onPressed: () => context.push('/customer/containers'),
                child: const Text('Find container space'),
              ),
            ],
          );
        },
      );
}

class _BookingItem extends StatelessWidget {
  const _BookingItem({required this.item, required this.index});
  final Map<String, dynamic> item;
  final int index;

  @override
  Widget build(BuildContext context) {
    final reference = item['booking_reference'] ?? item['sea_booking_id'] ?? item['id'] ?? 'Booking';
    final status = item['goods_status'] ?? item['payment_status'] ?? 'Status unavailable';
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
              BookingDetailPage(bookingId: '${item['sea_booking_id'] ?? item['id']}'),
        ),
      ),
    );
  }
}
