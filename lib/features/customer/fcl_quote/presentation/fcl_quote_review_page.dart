import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../../../features/repository_providers.dart';
import '../../presentation/customer_components.dart';

class _StepIndicator extends StatelessWidget {
  const _StepIndicator({required this.currentStep});
  final int currentStep;
  @override
  Widget build(BuildContext context) => Row(
    children: [
      for (var i = 0; i < 3; i++) ...[
        Column(
          children: [
            Container(
              width: 28, height: 28, alignment: Alignment.center,
              decoration: BoxDecoration(color: i <= currentStep ? brandCoral : appBorder, shape: BoxShape.circle),
              child: Text(i < currentStep ? '✓' : '${i + 1}', style: TextStyle(color: i <= currentStep ? Colors.white : appMuted, fontSize: 12, fontWeight: FontWeight.w700)),
            ),
            const SizedBox(height: 4),
            Text(['Route', 'Cargo', 'Review'][i], style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600)),
          ],
        ),
        if (i < 2) Expanded(child: Container(height: 2, color: i < currentStep ? brandCoral : appBorder)),
      ],
    ],
  );
}

class FclQuoteReviewPage extends ConsumerStatefulWidget {
  const FclQuoteReviewPage({this.quoteData, super.key});

  final Map<String, dynamic>? quoteData;

  @override
  ConsumerState<FclQuoteReviewPage> createState() => _FclQuoteReviewPageState();
}

class _FclQuoteReviewPageState extends ConsumerState<FclQuoteReviewPage> {
  bool _busy = false;

  Future<void> _submit() async {
    setState(() => _busy = true);
    try {
      final d = widget.quoteData ?? {};
      await ref.read(customerFclQuoteRepositoryProvider).createQuote({
        'request_type': 'FCL',
        'product': d['goods_type'] ?? 'FCL cargo',
        'specifications': '${d['container_size'] ?? ''} · ${d['weight'] ?? ''}',
        'supplier_status': 'needs_sourcing',
        'incoterm': 'FOB',
        'destination': '${d['destination_city'] ?? ''}, ${d['destination_country'] ?? ''}',
        'company_name': 'Customer',
        'business_license': 'N/A',
        'email': 'customer@sahajomy.co.tz',
        'whatsapp_number': '+0000000000',
      });
      if (mounted) context.go('/customer/fcl-quote/submitted');
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not submit: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final d = widget.quoteData ?? {};
    return CustomerScaffold(
      title: 'Review FCL request',
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          const _StepIndicator(currentStep: 2),
          const SizedBox(height: 20),
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(color: brandNavyDark, borderRadius: BorderRadius.circular(20)),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('REVIEW REQUEST', style: TextStyle(color: brandGold, fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 1.2)),
                const SizedBox(height: 8),
                const Text('One check before sending', style: TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w800)),
                const SizedBox(height: 8),
                const Text('Submitting sends the request to the platform workflow. It does not create a shipment booking.', style: TextStyle(color: Colors.white70, fontSize: 14)),
                const SizedBox(height: 16),
                Container(width: 44, height: 4, decoration: BoxDecoration(color: brandCoral, borderRadius: BorderRadius.circular(2))),
              ],
            ),
          ),
          const SizedBox(height: 20),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)),
            child: Column(
              children: [
                _kv('Route', '${d['origin_city'] ?? 'Yiwu'} → ${d['destination_city'] ?? 'Dar es Salaam'}'),
                const Divider(),
                _kv('Container', d['container_size'] ?? '40 ft'),
                const Divider(),
                _kv('Goods', d['goods_type'] ?? 'Furniture'),
                const Divider(),
                _kv('Weight', d['weight'] ?? '18,500 kg'),
                const Divider(),
                _kv('Ready', d['readiness'] ?? 'Within 7 days'),
              ],
            ),
          ),
          const SizedBox(height: 24),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Back'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: FilledButton(
                  onPressed: _busy ? null : _submit,
                  child: Text(_busy ? 'Submitting...' : 'Submit quote request'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

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
