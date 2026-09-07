import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../presentation/customer_components.dart';

class FclQuoteRequestsPage extends StatefulWidget {
  const FclQuoteRequestsPage({super.key});

  @override
  State<FclQuoteRequestsPage> createState() => _FclQuoteRequestsPageState();
}

class _FclQuoteRequestsPageState extends State<FclQuoteRequestsPage> {
  bool _active = true;

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'FCL quote requests',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        const CustomerHeroCard(
          eyebrow: 'FCL requests',
          title: 'Full container quote requests',
          subtitle: 'Track your FCL quote requests and operator responses in one place.',
        ),
        const SizedBox(height: 20),
        Row(
          children: [
            Expanded(
              child: FilledButton(
                onPressed: () => setState(() => _active = true),
                style: FilledButton.styleFrom(backgroundColor: _active ? brandCoral : appSurface),
                child: Text('Active', style: TextStyle(color: _active ? Colors.white : appMuted)),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: FilledButton(
                onPressed: () => setState(() => _active = false),
                style: FilledButton.styleFrom(backgroundColor: !_active ? brandCoral : appSurface),
                child: Text('Closed', style: TextStyle(color: !_active ? Colors.white : appMuted)),
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        _requestCard(
          ref: 'SAH-FCL-001234',
          route: 'Yiwu → Dar es Salaam',
          container: '40 ft',
          status: 'Pending',
          onTap: () => context.push('/customer/fcl-quote/requests/1'),
        ),
      ],
    ),
  );

  Widget _requestCard({
    required String ref,
    required String route,
    required String container,
    required String status,
    required VoidCallback onTap,
  }) =>
      GestureDetector(
        onTap: onTap,
        child: Container(
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)),
          child: Row(
            children: [
              Container(
                width: 44, height: 44, alignment: Alignment.center,
                decoration: BoxDecoration(color: brandGold.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(12)),
                child: const Text('FCL', style: TextStyle(color: brandGold, fontWeight: FontWeight.w800, fontSize: 11)),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(ref, style: const TextStyle(fontWeight: FontWeight.w800, fontFamily: 'monospace')),
                    const SizedBox(height: 2),
                    Text('$route · $container', style: const TextStyle(color: appMuted, fontSize: 13)),
                  ],
                ),
              ),
              CustomerStatusPill(label: status),
            ],
          ),
        ),
      );
}
