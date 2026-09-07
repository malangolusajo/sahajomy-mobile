import 'package:flutter/material.dart';
import '../../../../app/theme.dart';
import '../../../../core/ui/sahajomy_ui.dart';

class BookingSummaryCard extends StatelessWidget {
  const BookingSummaryCard({
    required this.entries,
    super.key,
    this.title,
    this.shippingMark,
    this.totalAmount,
    this.totalLabel,
  });

  final Map<String, Object?> entries;
  final String? title;
  final String? shippingMark;
  final String? totalAmount;
  final String? totalLabel;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (title != null) ...[
            Text(
              title!,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 16),
          ],
          SahajomyKeyValueList(entries: entries),
          if (shippingMark != null) ...[
            const SizedBox(height: 20),
            const Text(
              'Supplier shipping mark',
              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 14),
            ),
            const SizedBox(height: 8),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: appCanvas,
                borderRadius: BorderRadius.circular(radiusMd),
                border: Border.all(color: appBorder),
              ),
              child: Text(
                shippingMark!,
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: appInk,
                  letterSpacing: 0.3,
                ),
              ),
            ),
          ],
          if (totalAmount != null) ...[
            const SizedBox(height: 20),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: brandNavyDark,
                borderRadius: BorderRadius.circular(radiusMd),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    totalLabel ?? 'Estimated total',
                    style: const TextStyle(
                      fontSize: 14,
                      color: Color(0xFFD1DEE6),
                    ),
                  ),
                  Text(
                    totalAmount!,
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w900,
                      color: Colors.white,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    ),
  );
}
