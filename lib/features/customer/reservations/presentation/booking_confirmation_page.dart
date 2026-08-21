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
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
      children: [
        Text(
          'Space reserved',
          style: Theme.of(context).textTheme.headlineMedium,
        ),
        const SizedBox(height: 4),
        const Text(
          'Your request has been received. We will notify you once your booking is confirmed.',
        ),
        const SizedBox(height: 48),
        Center(
          child: Column(
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
              const SizedBox(height: 28),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFFF1F5F9),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Text(
                  'Next departure\n${reservation['route'] ?? 'Shanghai to Dar es Salaam'}${reservation['departure_date'] == null ? '' : ' · ${reservation['departure_date']}'}',
                  style: const TextStyle(
                    fontWeight: FontWeight.w700,
                    height: 1.6,
                  ),
                ),
              ),
              const SizedBox(height: 28),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: () =>
                      Navigator.pushNamed(context, '/customer/track-shipment'),
                  child: const Text('Track shipment'),
                ),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}
