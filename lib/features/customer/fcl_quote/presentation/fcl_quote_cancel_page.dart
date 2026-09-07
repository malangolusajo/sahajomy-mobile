import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../presentation/customer_components.dart';

class FclQuoteCancelPage extends StatefulWidget {
  const FclQuoteCancelPage({required this.requestId, super.key});

  final String requestId;

  @override
  State<FclQuoteCancelPage> createState() => _FclQuoteCancelPageState();
}

class _FclQuoteCancelPageState extends State<FclQuoteCancelPage> {
  String _reason = 'Found a better price elsewhere';

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Cancel FCL request',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(color: brandNavyDark, borderRadius: BorderRadius.circular(20)),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('CANCEL FCL REQUEST', style: TextStyle(color: brandGold, fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 1.2)),
              const SizedBox(height: 8),
              const Text('Cancel this FCL request?', style: TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w800)),
              const SizedBox(height: 8),
              const Text('Letting us know why helps us serve you better next time.', style: TextStyle(color: Colors.white70, fontSize: 14)),
              const SizedBox(height: 16),
              Container(width: 44, height: 4, decoration: BoxDecoration(color: brandCoral, borderRadius: BorderRadius.circular(2))),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(color: appError.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(12)),
          child: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Cancel request', style: TextStyle(fontWeight: FontWeight.w700, color: appError)),
              SizedBox(height: 4),
              Text('Cancelling closes this request. You can start a new one anytime.', style: TextStyle(color: appMuted, fontSize: 13)),
            ],
          ),
        ),
        const SizedBox(height: 16),
        DropdownButtonFormField<String>(
          value: _reason,
          decoration: const InputDecoration(labelText: 'Reason for cancelling'),
          items: const [
            'Found a better price elsewhere',
            'No longer need this shipment',
            'Changing route or container',
            'Other',
          ].map((s) => DropdownMenuItem(value: s, child: Text(s))).toList(),
          onChanged: (v) => setState(() => _reason = v ?? _reason),
        ),
        const SizedBox(height: 24),
        FilledButton(
          style: FilledButton.styleFrom(backgroundColor: appError),
          onPressed: () => context.go('/customer/fcl-quote/requests'),
          child: const Text('Cancel request'),
        ),
        const SizedBox(height: 12),
        OutlinedButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Keep request')),
      ],
    ),
  );
}
