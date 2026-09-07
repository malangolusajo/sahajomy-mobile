import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
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

class FclQuoteCargoPage extends StatefulWidget {
  const FclQuoteCargoPage({this.routeData, super.key});

  final Map<String, dynamic>? routeData;

  @override
  State<FclQuoteCargoPage> createState() => _FclQuoteCargoPageState();
}

class _FclQuoteCargoPageState extends State<FclQuoteCargoPage> {
  final _formKey = GlobalKey<FormState>();
  String _containerSize = '40 ft';
  String _goodsType = 'Furniture & home goods';
  final _weight = TextEditingController(text: '18,500 kg');
  String _readiness = 'Ready within 7 days';

  @override
  void dispose() {
    _weight.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Cargo details',
    body: Form(
      key: _formKey,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          const _StepIndicator(currentStep: 1),
          const SizedBox(height: 20),
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(color: brandNavyDark, borderRadius: BorderRadius.circular(20)),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('CARGO PROFILE', style: TextStyle(color: brandGold, fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 1.2)),
                const SizedBox(height: 8),
                const Text('Tell us what you are shipping', style: TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w800)),
                const SizedBox(height: 8),
                const Text('Enough detail helps the operator quote accurately without making this form difficult.', style: TextStyle(color: Colors.white70, fontSize: 14)),
                const SizedBox(height: 16),
                Container(width: 44, height: 4, decoration: BoxDecoration(color: brandCoral, borderRadius: BorderRadius.circular(2))),
              ],
            ),
          ),
          const SizedBox(height: 24),
          DropdownButtonFormField<String>(
            initialValue: _containerSize,
            decoration: const InputDecoration(labelText: 'Container size'),
            items: const ['20 ft', '40 ft', '40 ft High Cube'].map((s) => DropdownMenuItem(value: s, child: Text(s))).toList(),
            onChanged: (v) => setState(() => _containerSize = v ?? _containerSize),
          ),
          const SizedBox(height: 16),
          DropdownButtonFormField<String>(
            initialValue: _goodsType,
            decoration: const InputDecoration(labelText: 'Goods type'),
            items: const ['Furniture & home goods', 'Electronics', 'Clothing', 'Machinery', 'Other'].map((s) => DropdownMenuItem(value: s, child: Text(s))).toList(),
            onChanged: (v) => setState(() => _goodsType = v ?? _goodsType),
          ),
          const SizedBox(height: 16),
          TextFormField(
            controller: _weight,
            decoration: const InputDecoration(labelText: 'Estimated weight'),
            keyboardType: TextInputType.number,
          ),
          const SizedBox(height: 16),
          DropdownButtonFormField<String>(
            initialValue: _readiness,
            decoration: const InputDecoration(labelText: 'Cargo readiness'),
            items: const ['Ready within 7 days', 'Ready within 14 days', 'Ready within 30 days', 'Not ready yet'].map((s) => DropdownMenuItem(value: s, child: Text(s))).toList(),
            onChanged: (v) => setState(() => _readiness = v ?? _readiness),
          ),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(color: brandGold.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(12)),
            child: const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Have a packing list?', style: TextStyle(fontWeight: FontWeight.w700)),
                SizedBox(height: 4),
                Text('You can attach supporting details after submitting the quote request.', style: TextStyle(color: appMuted, fontSize: 13)),
              ],
            ),
          ),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: () {
              if (!_formKey.currentState!.validate()) return;
              context.push('/customer/fcl-quote/review', extra: {
                ...?widget.routeData,
                'container_size': _containerSize,
                'goods_type': _goodsType,
                'weight': _weight.text.trim(),
                'readiness': _readiness,
              });
            },
            child: const Text('Continue to review'),
          ),
        ],
      ),
    ),
  );
}
