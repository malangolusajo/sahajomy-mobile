import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../presentation/customer_components.dart';

class FclQuoteSubmittedPage extends StatelessWidget {
  const FclQuoteSubmittedPage({super.key});

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'FCL request submitted',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 28),
      children: [
        Column(
          children: [
            Container(
              width: 72, height: 72,
              decoration: BoxDecoration(color: appSuccess.withValues(alpha: 0.15), shape: BoxShape.circle),
              child: const Icon(Icons.check, size: 40, color: appSuccess),
            ),
            const SizedBox(height: 20),
            const Text('Quote request submitted', style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800)),
            const SizedBox(height: 8),
            const Text('Your FCL quote request has been saved. An operator will respond with pricing and next steps.', textAlign: TextAlign.center, style: TextStyle(color: appMuted)),
          ],
        ),
        const SizedBox(height: 28),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)),
          child: const Row(
            children: [
              CircleAvatar(radius: 20, backgroundColor: brandGold, child: Text('FCL', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 12))),
              SizedBox(width: 14),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('SAH-FCL-XXXXXX', style: TextStyle(fontWeight: FontWeight.w800, fontFamily: 'monospace')),
                SizedBox(height: 2),
                Text('Awaiting operator quote', style: TextStyle(color: appMuted, fontSize: 13)),
              ])),
            ],
          ),
        ),
        const SizedBox(height: 24),
        Row(
          children: [
            Expanded(
              child: FilledButton(
                onPressed: () => context.go('/customer/fcl-quote/requests'),
                child: const Text('View request'),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        OutlinedButton(
          onPressed: () => context.go('/customer'),
          child: const Text('Back to home'),
        ),
      ],
    ),
  );
}
