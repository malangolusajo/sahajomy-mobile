import 'package:flutter/material.dart';
import '../../../../app/theme.dart';
import '../../../../core/ui/sahajomy_ui.dart';

class ServiceSelectionCard extends StatelessWidget {
  const ServiceSelectionCard({
    required this.title,
    required this.route,
    required this.availableText,
    required this.statusText,
    required this.priceText,
    required this.onTap,
    super.key,
    this.operator,
    this.departureDate,
    this.isRecommended = false,
  });

  final String title;
  final String route;
  final String availableText;
  final String statusText;
  final String priceText;
  final VoidCallback? onTap;
  final String? operator;
  final String? departureDate;
  final bool isRecommended;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    if (operator != null) ...[
                      const SizedBox(height: 2),
                      Text(
                        operator!,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ],
                ),
              ),
              if (isRecommended)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: brandCoralLight,
                    borderRadius: BorderRadius.circular(radiusRound),
                  ),
                  child: const Text(
                    'RECOMMENDED',
                    style: TextStyle(
                      fontSize: 9,
                      fontWeight: FontWeight.w800,
                      color: brandCoral,
                      letterSpacing: 0.5,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              const Icon(Icons.route_outlined, size: 16, color: brandNavy),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  route,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: appInk,
                  ),
                ),
              ),
            ],
          ),
          if (departureDate != null) ...[
            const SizedBox(height: 8),
            Row(
              children: [
                const Icon(Icons.calendar_today_outlined, size: 14, color: appMuted),
                const SizedBox(width: 6),
                Text(
                  departureDate!,
                  style: const TextStyle(fontSize: 13, color: appMuted),
                ),
              ],
            ),
          ],
          const SizedBox(height: 12),
          Wrap(
            spacing: 12,
            runSpacing: 8,
            children: [
              SahajomyStatusPill(label: statusText),
              Text(
                priceText,
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: appInk,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              onPressed: onTap,
              child: const Text('Select'),
            ),
          ),
        ],
      ),
    ),
  );
}
