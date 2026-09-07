import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../presentation/customer_components.dart';

class FclQuoteRoutePage extends StatefulWidget {
  const FclQuoteRoutePage({super.key});

  @override
  State<FclQuoteRoutePage> createState() => _FclQuoteRoutePageState();
}

class _FclQuoteRoutePageState extends State<FclQuoteRoutePage> {
  final _formKey = GlobalKey<FormState>();
  final _originCity = TextEditingController(text: 'Yiwu, Zhejiang');
  final _destinationCountry = TextEditingController(text: 'Tanzania');
  final _destinationCity = TextEditingController(text: 'Dar es Salaam');

  @override
  void dispose() {
    _originCity.dispose();
    _destinationCountry.dispose();
    _destinationCity.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Request FCL quote',
    body: Form(
      key: _formKey,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          const _StepIndicator(currentStep: 0),
          const SizedBox(height: 20),
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: brandNavyDark,
              borderRadius: BorderRadius.circular(20),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('FCL QUOTE', style: TextStyle(color: brandGold, fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 1.2)),
                const SizedBox(height: 8),
                const Text('Where should it move?', style: TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w800)),
                const SizedBox(height: 8),
                const Text('Choose the China origin and final destination so operators can price the correct route.', style: TextStyle(color: Colors.white70, fontSize: 14)),
                const SizedBox(height: 16),
                Container(width: 44, height: 4, decoration: BoxDecoration(color: brandCoral, borderRadius: BorderRadius.circular(2))),
              ],
            ),
          ),
          const SizedBox(height: 24),
          TextFormField(
            controller: _originCity,
            decoration: const InputDecoration(labelText: 'Origin city'),
            validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
          ),
          const SizedBox(height: 16),
          TextFormField(
            controller: _destinationCountry,
            decoration: const InputDecoration(labelText: 'Destination country'),
            validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
          ),
          const SizedBox(height: 16),
          TextFormField(
            controller: _destinationCity,
            decoration: const InputDecoration(labelText: 'Destination city / port'),
            validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
          ),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: () {
              if (!_formKey.currentState!.validate()) return;
              context.push('/customer/fcl-quote/cargo', extra: {
                'origin_city': _originCity.text.trim(),
                'destination_country': _destinationCountry.text.trim(),
                'destination_city': _destinationCity.text.trim(),
              });
            },
            child: const Text('Continue to cargo'),
          ),
        ],
      ),
    ),
  );
}

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
              width: 28,
              height: 28,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: i <= currentStep ? brandCoral : appBorder,
                shape: BoxShape.circle,
              ),
              child: Text(
                i < currentStep ? '✓' : '${i + 1}',
                style: TextStyle(color: i <= currentStep ? Colors.white : appMuted, fontSize: 12, fontWeight: FontWeight.w700),
              ),
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
