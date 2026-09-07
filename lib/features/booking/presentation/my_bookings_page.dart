import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import '../../../core/ui/logistics_ui.dart';
import '../../../core/ui/sahajomy_ui.dart';
import '../../repository_providers.dart';

class MyBookingsPage extends ConsumerStatefulWidget {
  const MyBookingsPage({super.key});

  @override
  ConsumerState<MyBookingsPage> createState() => _MyBookingsPageState();
}

class _MyBookingsPageState extends ConsumerState<MyBookingsPage> {
  late Future<List<Map<String, dynamic>>> _seaBookings;
  late Future<List<Map<String, dynamic>>> _airBookings;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    setState(() {
      _seaBookings = ref
          .read(customerBookingRepositoryProvider)
          .listBookings();
      _airBookings = ref
          .read(customerAirCargoRepositoryProvider)
          .listBookings();
    });
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: const SahajomyScreenHeader(
          role: 'Customer',
          title: 'My bookings',
          showBack: false,
        ),
        body: RefreshIndicator(
          onRefresh: () async => _load(),
          child: ListView(
            padding: const EdgeInsets.fromLTRB(24, 16, 24, 32),
            children: [
              FutureBuilder<List<Map<String, dynamic>>>(
                future: _seaBookings,
                builder: (context, snapshot) {
                  if (snapshot.connectionState != ConnectionState.done) {
                    return const Padding(
                      padding: EdgeInsets.symmetric(vertical: 32),
                      child: Center(child: CircularProgressIndicator()),
                    );
                  }
                  if (snapshot.hasError) {
                    return SahajomyMessageState(
                      icon: Icons.cloud_off_outlined,
                      message: logisticsError(
                          snapshot.error, 'sea freight bookings'),
                      actionLabel: 'Reload',
                      onAction: _load,
                    );
                  }
                  final bookings = snapshot.data ?? [];
                  if (bookings.isEmpty) {
                    return const SizedBox.shrink();
                  }
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Sea freight',
                          style: Theme.of(context).textTheme.titleLarge),
                      const SizedBox(height: 12),
                      for (final booking in bookings)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: _BookingRow(
                            record: booking,
                            type: 'sea',
                            onTap: () => context.push(
                                '/customer/sea-bookings/${booking['id']}'),
                          ),
                        ),
                      const SizedBox(height: 12),
                    ],
                  );
                },
              ),
              FutureBuilder<List<Map<String, dynamic>>>(
                future: _airBookings,
                builder: (context, snapshot) {
                  if (snapshot.connectionState != ConnectionState.done) {
                    return const SizedBox.shrink();
                  }
                  if (snapshot.hasError) {
                    return const SizedBox.shrink();
                  }
                  final bookings = snapshot.data ?? [];
                  if (bookings.isEmpty) {
                    return const SizedBox.shrink();
                  }
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Air cargo',
                          style: Theme.of(context).textTheme.titleLarge),
                      const SizedBox(height: 12),
                      for (final booking in bookings)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: _BookingRow(
                            record: booking,
                            type: 'air',
                          ),
                        ),
                    ],
                  );
                },
              ),
            ],
          ),
        ),
      );
}

class _BookingRow extends StatelessWidget {
  const _BookingRow({
    required this.record,
    required this.type,
    this.onTap,
  });

  final Map<String, dynamic> record;
  final String type;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final ref = record['booking_reference'] ??
        record['tracking_number'] ??
        record['id'] ??
        'Booking';
    final route = record['route'] ??
        (record['destination_region'] != null
            ? 'To ${record['destination_region']}'
            : null);
    final status = record['status'] ??
        record['payment_status'] ??
        record['goods_status'];

    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(radiusXl),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: type == 'sea'
                      ? brandTeal.withValues(alpha: 0.1)
                      : brandCoral.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(radiusMd),
                ),
                alignment: Alignment.center,
                child: Icon(
                  type == 'sea'
                      ? Icons.directions_boat_outlined
                      : Icons.flight_outlined,
                  size: 22,
                  color: type == 'sea' ? brandTeal : brandCoral,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '$ref',
                      style: const TextStyle(
                        fontWeight: FontWeight.w800,
                        color: appInk,
                      ),
                    ),
                    if (route != null) ...[
                      const SizedBox(height: 4),
                      Text(
                        '$route',
                        style: const TextStyle(
                            fontSize: 13, color: appMuted),
                      ),
                    ],
                    if (status != null) ...[
                      const SizedBox(height: 6),
                      SahajomyStatusPill(label: '$status'),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: 8),
              const Icon(Icons.chevron_right_rounded,
                  color: appMuted, size: 20),
            ],
          ),
        ),
      ),
    );
  }
}
