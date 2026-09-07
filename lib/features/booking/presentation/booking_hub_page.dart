import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import '../../../core/ui/sahajomy_ui.dart';

class BookingHubPage extends StatelessWidget {
  const BookingHubPage({super.key});

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(
      role: 'Customer',
      title: 'Book shipment',
      showBack: false,
    ),
    body: ListView(
      padding: const EdgeInsets.fromLTRB(24, 16, 24, 32),
      children: [
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(28),
          decoration: BoxDecoration(
            color: brandNavyDark,
            borderRadius: BorderRadius.circular(radiusXl),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'How are you\nshipping?',
                style: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.w900,
                  color: Colors.white,
                  height: 1.15,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Choose the best option for your cargo.',
                style: TextStyle(color: Color(0xFFD1DEE6), fontSize: 14),
              ),
            ],
          ),
        ),
        const SizedBox(height: 28),
        _ShippingOption(
          icon: Icons.directions_boat_outlined,
          title: 'Sea cargo',
          description: 'Cost-effective for large or bulk shipments',
          color: brandTeal,
          onTap: () => context.push('/customer/booking/sea-services'),
        ),
        const SizedBox(height: 14),
        _ShippingOption(
          icon: Icons.flight_outlined,
          title: 'Air cargo',
          description: 'Fastest option for time-sensitive goods',
          color: brandCoral,
          onTap: () => context.push('/customer/booking/air-services'),
        ),
        const SizedBox(height: 14),
        _ShippingOption(
          icon: Icons.inventory_2_outlined,
          title: 'FCL cargo',
          description: 'Full container load for large volume',
          color: brandNavy,
          onTap: () {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('FCL booking coming soon')),
            );
          },
        ),
      ],
    ),
  );
}

class _ShippingOption extends StatelessWidget {
  const _ShippingOption({
    required this.icon,
    required this.title,
    required this.description,
    required this.color,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String description;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Card(
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(radiusXl),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            Container(
              width: 52,
              height: 52,
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(radiusLg),
              ),
              alignment: Alignment.center,
              child: Icon(icon, size: 26, color: color),
            ),
            const SizedBox(width: 18),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w800,
                      color: appInk,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    description,
                    style: const TextStyle(fontSize: 13, color: appMuted),
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right_rounded, color: appMuted),
          ],
        ),
      ),
    ),
  );
}
