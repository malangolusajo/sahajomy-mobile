import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import '../../../core/ui/logistics_ui.dart';
import '../../../core/ui/sahajomy_ui.dart';
import '../../customer/presentation/customer_components.dart';
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
      _seaBookings = ref.read(customerBookingRepositoryProvider).listBookings();
      _airBookings = ref
          .read(customerAirCargoRepositoryProvider)
          .listBookings();
    });
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'My bookings',
    body: RefreshIndicator(
      onRefresh: () async => _load(),
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
        children: [
          const CustomerHeroCard(
            eyebrow: 'Bookings',
            title: 'My bookings',
            subtitle: 'Track your sea and air cargo bookings, payments and documents.',
          ),
          const SizedBox(height: 24),
          FutureBuilder<List<Map<String, dynamic>>>(
            future: _seaBookings,
            builder: (context, snapshot) {
              if (snapshot.connectionState != ConnectionState.done) {
                return const CustomerSkeletonList();
              }
              if (snapshot.hasError) {
                return SahajomyMessageState(
                  icon: Icons.cloud_off_outlined,
                  message: logisticsError(
                    snapshot.error,
                    'sea freight bookings',
                  ),
                  actionLabel: 'Reload',
                  onAction: _load,
                );
              }
              final bookings = snapshot.data ?? [];
              if (bookings.isEmpty) return const SizedBox.shrink();
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Sea freight',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w800,
                      color: appInk,
                    ),
                  ),
                  const SizedBox(height: 12),
                  for (final booking in bookings)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: _BookingRow(
                        record: booking,
                        type: 'sea',
                        onTap: () => context.push(
                          '/customer/sea-bookings/${booking['id']}',
                        ),
                      ),
                    ),
                ],
              );
            },
          ),
          const SizedBox(height: 24),
          FutureBuilder<List<Map<String, dynamic>>>(
            future: _airBookings,
            builder: (context, snapshot) {
              if (snapshot.connectionState != ConnectionState.done) {
                return const SizedBox.shrink();
              }
              if (snapshot.hasError) return const SizedBox.shrink();
              final bookings = snapshot.data ?? [];
              if (bookings.isEmpty) return const SizedBox.shrink();
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Air cargo',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w800,
                      color: appInk,
                    ),
                  ),
                  const SizedBox(height: 12),
                  for (final booking in bookings)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: _BookingRow(record: booking, type: 'air'),
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
  const _BookingRow({required this.record, required this.type, this.onTap});

  final Map<String, dynamic> record;
  final String type;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final ref =
        record['booking_reference'] ??
        record['tracking_number'] ??
        record['id'] ??
        'Booking';
    final route =
        record['route'] ??
        (record['destination_region'] != null
            ? 'To ${record['destination_region']}'
            : 'Route pending');
    final status =
        record['status'] ??
        record['payment_status'] ??
        record['goods_status'] ??
        'Processing';
    final cbm = record['cbm_booked'] ?? record['booked_cbm'];
    final weight = record['weight_kg'] ?? record['gross_weight'];
    final detail = cbm != null
        ? '$route · $cbm CBM'
        : (weight != null ? '$route · $weight kg' : '$route');

    return CustomerListItem(
      badgeLabel: type == 'sea' ? 'SEA' : 'AIR',
      badgeColor: type == 'sea' ? brandCoral : brandNavy,
      title: ref,
      subtitle: detail,
      status: status.toString().replaceAll('_', ' '),
      onTap: onTap,
    );
  }
}
