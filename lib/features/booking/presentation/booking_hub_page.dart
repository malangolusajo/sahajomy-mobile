import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import '../../customer/presentation/customer_components.dart';

class BookingHubPage extends StatelessWidget {
  const BookingHubPage({super.key});

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Book shipment',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
      children: [
        const CustomerHeroCard(
          eyebrow: 'Book shipment',
          title: 'How are you shipping?',
          subtitle: 'Choose the service that fits your cargo. You can review pricing and operator details before confirming.',
        ),
        const SizedBox(height: 24),
        _ShippingOption(
          badge: 'SEA',
          badgeColor: brandCoral,
          title: 'Sea cargo',
          description: 'Shared container space by CBM',
          onTap: () => context.push('/customer/booking/sea-services'),
        ),
        const SizedBox(height: 12),
        _ShippingOption(
          badge: 'AIR',
          badgeColor: brandNavy,
          title: 'Air cargo',
          description: 'Faster shipping priced by weight',
          onTap: () => context.push('/customer/booking/air-services'),
        ),
        const SizedBox(height: 12),
        _ShippingOption(
          badge: 'FCL',
          badgeColor: brandNavy,
          title: 'Full Container Load',
          description: 'Request a dedicated container quote',
          onTap: () => context.push('/customer/fcl-quote'),
        ),
      ],
    ),
  );
}

class _ShippingOption extends StatelessWidget {
  const _ShippingOption({
    required this.badge,
    required this.badgeColor,
    required this.title,
    required this.description,
    required this.onTap,
  });

  final String badge;
  final Color badgeColor;
  final String title;
  final String description;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
    color: Colors.white,
    borderRadius: BorderRadius.circular(16),
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: appBorder, width: 1),
        ),
        child: Row(
          children: [
            Container(
              width: 44,
              height: 44,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: badgeColor.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                badge,
                style: TextStyle(
                  color: badgeColor,
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w800,
                      color: appInk,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    description,
                    style: const TextStyle(fontSize: 12.5, color: appMuted),
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right_rounded, color: appMuted, size: 20),
          ],
        ),
      ),
    ),
  );
}
