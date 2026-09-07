import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../presentation/customer_components.dart';

class FclQuoteDetailPage extends StatelessWidget {
  const FclQuoteDetailPage({required this.requestId, super.key});

  final String requestId;

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'FCL quote request',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(color: brandNavyDark, borderRadius: BorderRadius.circular(20)),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('FCL REQUEST', style: TextStyle(color: brandGold, fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 1.2)),
              const SizedBox(height: 8),
              Text('SAH-FCL-$requestId', style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w800, fontFamily: 'monospace')),
              const SizedBox(height: 8),
              const Text('Yiwu → Dar es Salaam · 40 ft', style: TextStyle(color: Colors.white70, fontSize: 14)),
              const SizedBox(height: 16),
              Container(width: 44, height: 4, decoration: BoxDecoration(color: brandCoral, borderRadius: BorderRadius.circular(2))),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(color: brandGold.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(12)),
          child: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Operator response ready', style: TextStyle(fontWeight: FontWeight.w700)),
              SizedBox(height: 4),
              Text('Review the quoted amount and accept to proceed with booking.', style: TextStyle(color: appMuted, fontSize: 13)),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)),
          child: Column(
            children: [
              _kv('Quoted amount', 'USD 2,150'),
              const Divider(),
              _kv('Transit days', '28 days'),
              const Divider(),
              _kv('Free days at port', '7 days'),
              const Divider(),
              _kv('Valid until', '15 Jun 2025'),
            ],
          ),
        ),
        const SizedBox(height: 24),
        FilledButton(onPressed: () => context.push('/customer/fcl-quote/requests/$requestId/cancel'), child: const Text('Cancel request')),
        const SizedBox(height: 12),
        OutlinedButton(onPressed: () => context.go('/customer/fcl-quote/requests'), child: const Text('Back to requests')),
      ],
    ),
  );

  Widget _kv(String label, String value) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 8),
    child: Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: const TextStyle(color: appMuted, fontSize: 14)),
        Text(value, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
      ],
    ),
  );
}
