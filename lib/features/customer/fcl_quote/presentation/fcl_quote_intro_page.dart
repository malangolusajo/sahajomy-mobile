import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../presentation/customer_components.dart';

class FclQuoteIntroPage extends StatelessWidget {
  const FclQuoteIntroPage({super.key});

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Full Container Load',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: brandNavyDark,
            borderRadius: BorderRadius.circular(20),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'FULL CONTAINER LOAD',
                style: TextStyle(color: brandGold, fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 1.2),
              ),
              const SizedBox(height: 8),
              const Text(
                'Need the whole container?',
                style: TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 8),
              const Text(
                'Request a tailored FCL quote for high-volume cargo from China to your destination.',
                style: TextStyle(color: Colors.white70, fontSize: 14),
              ),
              const SizedBox(height: 16),
              Container(width: 44, height: 4, decoration: BoxDecoration(color: brandCoral, borderRadius: BorderRadius.circular(2))),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: appBorder),
          ),
          child: const Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _Stat(label: 'Best for', value: '20ft / 40ft'),
              _Stat(label: 'Pricing', value: 'Quoted'),
              _Stat(label: 'Support', value: 'Operator-led'),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Container(
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: appBorder),
          ),
          child: Column(
            children: [
              _sizeRow('20', '20 ft container', 'Suitable for compact full-load shipments'),
              const Divider(height: 1, indent: 60),
              _sizeRow('40', '40 ft container', 'More capacity for larger consignments'),
              const Divider(height: 1, indent: 60),
              _sizeRow('HC', '40 ft High Cube', 'Extra vertical capacity where available'),
            ],
          ),
        ),
        const SizedBox(height: 24),
        FilledButton(
          onPressed: () => context.push('/customer/fcl-quote/route'),
          child: const Text('Request an FCL quote'),
        ),
      ],
    ),
  );

  Widget _sizeRow(String badge, String title, String subtitle) => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    child: Row(
      children: [
        Container(
          width: 40,
          height: 40,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: appMuted.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Text(badge, style: const TextStyle(color: appMuted, fontWeight: FontWeight.w800)),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
              const SizedBox(height: 2),
              Text(subtitle, style: const TextStyle(color: appMuted, fontSize: 13)),
            ],
          ),
        ),
        const Icon(Icons.chevron_right, color: appMuted),
      ],
    ),
  );
}

class _Stat extends StatelessWidget {
  const _Stat({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Column(
    children: [
      Text(label, style: const TextStyle(color: appMuted, fontSize: 11)),
      const SizedBox(height: 4),
      Text(value, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14)),
    ],
  );
}
