import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import '../../../core/ui/logistics_ui.dart';
import '../../customer/presentation/customer_components.dart';
import '../../repository_providers.dart';
import '../../customer/air_cargo/data/customer_air_cargo_repository.dart';
import 'components/booking_step_indicator.dart';
import 'components/booking_summary_card.dart';

class AirReviewBookingPage extends ConsumerStatefulWidget {
  const AirReviewBookingPage({
    required this.warehouseId,
    required this.cargoAdminId,
    required this.companyName,
    required this.warehouseName,
    required this.cargoTypeId,
    required this.weight,
    required this.destination,
    required this.country,
    required this.cartons,
    required this.shipmentDate,
    this.description,
    super.key,
  });

  final String warehouseId;
  final String cargoAdminId;
  final String companyName;
  final String warehouseName;
  final String cargoTypeId;
  final String weight;
  final String destination;
  final String country;
  final String cartons;
  final String shipmentDate;
  final String? description;

  @override
  ConsumerState<AirReviewBookingPage> createState() =>
      _AirReviewBookingPageState();
}

class _AirReviewBookingPageState extends ConsumerState<AirReviewBookingPage> {
  Map<String, dynamic>? _booking;
  bool _busy = false;
  String? _error;
  bool _confirmed = false;

  CustomerAirCargoRepository get _repo =>
      ref.read(customerAirCargoRepositoryProvider);

  Future<void> _confirm() async {
    if (_busy || _confirmed) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final address = await _repo.prepareAddress(
        city: widget.destination,
        country: widget.country,
        cargoAdminId: widget.cargoAdminId,
        warehouseId: widget.warehouseId,
      );
      if (!mounted) return;

      final result = await _repo.createBooking(
        cargoTypeId: widget.cargoTypeId,
        weightKg: double.parse(widget.weight),
        shipmentDate: DateTime.parse(widget.shipmentDate),
        destinationRegion: widget.destination,
        cartonCount: int.parse(widget.cartons),
        destinationCountry: widget.country,
        cargoAdminId: widget.cargoAdminId,
        warehouseId: widget.warehouseId,
        chinaAddressId: '${address['id']}',
        cargoDescription: widget.description,
      );
      if (mounted) {
        setState(() {
          _booking = result;
          _confirmed = true;
          _busy = false;
        });
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _error = logisticsError(error, 'air cargo booking');
          _busy = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_confirmed && _booking != null) {
      return _buildConfirmation();
    }

    final dateStr =
        '${DateTime.parse(widget.shipmentDate).year}-${DateTime.parse(widget.shipmentDate).month.toString().padLeft(2, '0')}-${DateTime.parse(widget.shipmentDate).day.toString().padLeft(2, '0')}';

    return CustomerScaffold(
      title: 'Review booking',
      body: ListView(
        padding: const EdgeInsets.fromLTRB(24, 12, 24, 32),
        children: [
          const BookingStepIndicator(
            steps: ['Service', 'Cargo details', 'Review'],
            currentStep: 2,
          ),
          const SizedBox(height: 24),
          const CustomerHeroCard(
            eyebrow: 'Express Air Cargo',
            title: 'Review booking',
            subtitle:
                'Confirm your air cargo booking details before submitting.',
          ),
          const SizedBox(height: 24),
          BookingSummaryCard(
            title: 'Booking summary',
            entries: {
              'Cargo company': widget.companyName,
              'Warehouse': widget.warehouseName,
              'Weight': '${widget.weight} kg',
              'Destination': '${widget.destination}, ${widget.country}',
              'Cartons': widget.cartons,
              'Shipment date': dateStr,
              'Freight rate': 'Quotation required',
            },
          ),
          if (_error != null) ...[
            const SizedBox(height: 16),
            Text(_error!, style: const TextStyle(color: appError)),
          ],
          const SizedBox(height: 28),
          FilledButton(
            onPressed: _busy ? null : _confirm,
            child: Text(
              _busy ? 'Confirming booking...' : 'Confirm air booking',
            ),
          ),
          TextButton(
            onPressed: _busy ? null : () => context.pop(),
            child: const Text('Edit cargo details'),
          ),
        ],
      ),
    );
  }

  Widget _buildConfirmation() {
    final ref =
        _booking!['tracking_number'] ??
        _booking!['booking_reference'] ??
        _booking!['id'] ??
        'Pending';

    return CustomerScaffold(
      title: 'Booking confirmed',
      body: ListView(
        padding: const EdgeInsets.fromLTRB(24, 12, 24, 32),
        children: [
          const SizedBox(height: 32),
          const Icon(
            Icons.check_circle_outline_rounded,
            size: 72,
            color: appSuccess,
          ),
          const SizedBox(height: 24),
          Text(
            'Booking confirmed',
            style: Theme.of(context).textTheme.headlineMedium,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 8),
          Text(
            'Your air cargo booking has been created successfully.',
            style: Theme.of(context).textTheme.bodyLarge,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 32),
          BookingSummaryCard(
            entries: {
              'Tracking number': ref,
              'Cargo company': widget.companyName,
              'Weight': '${widget.weight} kg',
              'Destination': '${widget.destination}, ${widget.country}',
            },
          ),
          const SizedBox(height: 28),
          FilledButton(
            onPressed: () => context.go('/customer/my-bookings'),
            child: const Text('View my bookings'),
          ),
          TextButton(
            onPressed: () => context.go('/customer'),
            child: const Text('Back to home'),
          ),
        ],
      ),
    );
  }
}
