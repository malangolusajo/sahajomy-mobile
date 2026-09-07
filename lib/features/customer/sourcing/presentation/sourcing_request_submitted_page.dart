import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../presentation/customer_components.dart';

class SourcingRequestSubmittedPage extends StatelessWidget {
  const SourcingRequestSubmittedPage({this.reference, super.key});

  final String? reference;

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Request submitted',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 28),
      children: [
        Column(
          children: [
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                color: appSuccess.withValues(alpha: 0.15),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.check, size: 40, color: appSuccess),
            ),
            const SizedBox(height: 20),
            const Text(
              'Request submitted',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 8),
            const Text(
              'Your request has been recorded. The next relevant step is shown below.',
              textAlign: TextAlign.center,
              style: TextStyle(color: appMuted),
            ),
          ],
        ),
        const SizedBox(height: 28),
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
                      reference ?? 'SAH-XXXXXX-XXXX',
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
          onPressed: () => context.go('/customer'),
          child: const Text('Continue'),
        ),
      ],
    ),
  );
}
