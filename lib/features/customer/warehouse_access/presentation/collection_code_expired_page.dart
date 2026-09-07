import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../presentation/customer_components.dart';

class CollectionCodeExpiredPage extends StatelessWidget {
  const CollectionCodeExpiredPage({this.reference, super.key});

  final String? reference;

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Collection code expired',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 28),
      children: [
        Column(
          children: [
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                color: appWarning.withValues(alpha: 0.15),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.error_outline, size: 40, color: appWarning),
            ),
            const SizedBox(height: 20),
            const Text(
              'Collection code expired',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 8),
            const Text(
              'Generate a fresh collection request before handing over any parcels.',
              textAlign: TextAlign.center,
              style: TextStyle(color: appMuted),
            ),
          ],
        ),
        const SizedBox(height: 28),
        if (reference != null)
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: appBorder),
            ),
            child: Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: brandGold.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Text('REF', style: TextStyle(color: brandGold, fontWeight: FontWeight.w800, fontSize: 12)),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        reference!,
                        style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15, fontFamily: 'monospace'),
                      ),
                      const SizedBox(height: 2),
                      const Text('Reference saved to your account', style: TextStyle(color: appMuted, fontSize: 13)),
                    ],
                  ),
                ),
              ],
            ),
          ),
        const SizedBox(height: 24),
        FilledButton(
          onPressed: () => context.go('/customer/collection'),
          child: const Text('Continue'),
        ),
      ],
    ),
  );
}
