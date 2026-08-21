import 'package:flutter/material.dart';

import '../../../../core/ui/sahajomy_ui.dart';

class BookingConfirmationPage extends StatelessWidget {
  const BookingConfirmationPage({required this.reservation, super.key});
  final Map<String, dynamic> reservation;
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(
      role: 'Customer',
      title: 'Booking confirmed',
    ),
    body: Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const CircleAvatar(
              radius: 40,
              backgroundColor: Color(0xFFD1FAE5),
              child: Icon(Icons.check, size: 42, color: Color(0xFF059669)),
            ),
            const SizedBox(height: 28),
            Text(
              'Space reserved',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 12),
            Text(
              'Reservation #${reservation['reservation_number'] ?? reservation['id'] ?? ''} is under review. We will send an update when it is confirmed.',
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: () =>
                  Navigator.pushNamed(context, '/customer/track-shipment'),
              child: const Text('Track shipment'),
            ),
          ],
        ),
      ),
    ),
  );
}
