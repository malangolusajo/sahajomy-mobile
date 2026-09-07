import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import '../../../core/ui/logistics_ui.dart';
import '../../../core/ui/sahajomy_ui.dart';
import '../../repository_providers.dart';
import '../data/guided_booking_repository.dart';
import 'components/booking_step_indicator.dart';
import 'components/booking_summary_card.dart';

class SeaReviewBookingPage extends ConsumerStatefulWidget {
  const SeaReviewBookingPage({
    required this.containerId,
    required this.routeName,
    required this.volume,
    required this.goodsType,
    required this.description,
    required this.quantity,
    this.cartons,
    super.key,
  });

  final String containerId;
  final String routeName;
  final String volume;
  final String goodsType;
  final String description;
  final String quantity;
  final String? cartons;

  @override
  ConsumerState<SeaReviewBookingPage> createState() => _SeaReviewBookingPageState();
}

class _SeaReviewBookingPageState extends ConsumerState<SeaReviewBookingPage> {
  Map<String, dynamic>? _booking;
  bool _busy = false;
  String? _error;
  bool _confirmed = false;

  GuidedBookingRepository get _repo => ref.read(guidedBookingRepositoryProvider);

  Future<void> _confirm() async {
    if (_busy || _confirmed) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await _repo.prepareSeaAddress(
        containerId: widget.containerId,
        destinationCity: '',
        destinationCountry: '',
      );
      if (!mounted) return;

      final payload = <String, dynamic>{
        'container_id': widget.containerId,
        'booked_cbm': double.parse(widget.volume),
        'goods_types': [widget.goodsType],
        'cargo_description': widget.description,
      };
      if (widget.cartons != null && widget.cartons!.isNotEmpty) {
        payload['carton_count'] = int.parse(widget.cartons!);
      }

      final booking = await _repo.confirmSeaBooking(
        account: BookingAccount.customer,
        payload: payload,
      );
      if (mounted) {
        setState(() {
          _booking = booking;
          _confirmed = true;
          _busy = false;
        });
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _error = logisticsError(error, 'cargo booking');
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

    return Scaffold(
      appBar: const SahajomyScreenHeader(
        role: 'Customer',
        title: 'Review booking',
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(24, 16, 24, 32),
        children: [
          const BookingStepIndicator(
            steps: ['Service', 'Cargo details', 'Review'],
            currentStep: 2,
          ),
          const SizedBox(height: 24),
          BookingSummaryCard(
            title: 'Booking summary',
            entries: {
              'Route': widget.routeName,
              'Goods type': widget.goodsType,
              'Description': widget.description,
              'Quantity': widget.quantity,
              'Volume': '${widget.volume} CBM',
              if (widget.cartons != null && widget.cartons!.isNotEmpty)
                'Cartons': widget.cartons,
            },
          ),
          if (_error != null) ...[
            const SizedBox(height: 16),
            Text(_error!, style: const TextStyle(color: appError)),
          ],
          const SizedBox(height: 28),
          FilledButton(
            onPressed: _busy ? null : _confirm,
            child: Text(_busy ? 'Confirming booking...' : 'Confirm booking'),
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
    final ref = _booking!['booking_reference'] ??
        _booking!['sea_booking_id'] ??
        _booking!['id'] ??
        'Pending';

    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(24, 24, 24, 32),
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
              'Your sea freight booking has been created successfully.',
              style: Theme.of(context).textTheme.bodyLarge,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 32),
            BookingSummaryCard(
              entries: {
                'Booking reference': ref,
                'Route': widget.routeName,
                'Volume': '${widget.volume} CBM',
                'Goods type': widget.goodsType,
                if (_booking!['logistics_charge'] != null)
                  'Freight charge': '${_booking!['logistics_charge']} ${_booking!['currency'] ?? ''}',
                if (_booking!['payment_status'] != null)
                  'Payment status': sahajomyTitleCase('${_booking!['payment_status']}'),
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
      ),
    );
  }
}
