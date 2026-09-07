import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../../../features/repository_providers.dart';
import '../../../customer/presentation/customer_components.dart';

class CargoTrackingUpdatePage extends StatelessWidget {
  const CargoTrackingUpdatePage({required this.entityId, super.key});
  final String entityId;

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'TRACKING',
    title: 'Update tracking',
    notificationRoute: '/cargo/notifications',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        const CustomerHeroCard(eyebrow: 'Tracking', title: 'Log a tracking event', subtitle: 'Customers see this update on their shipment timeline.'),
        const SizedBox(height: 24),
        const TextField(decoration: InputDecoration(labelText: 'Event description'), maxLines: 3),
        const SizedBox(height: 16),
        DropdownButtonFormField(initialValue: 'in_transit', decoration: const InputDecoration(labelText: 'Status'), items: const [
          DropdownMenuItem(value: 'received', child: Text('Received at warehouse')),
          DropdownMenuItem(value: 'in_transit', child: Text('In transit')),
          DropdownMenuItem(value: 'arrived', child: Text('Arrived at destination')),
          DropdownMenuItem(value: 'ready_for_collection', child: Text('Ready for collection')),
        ], onChanged: null),
        const SizedBox(height: 24),
        FilledButton(onPressed: () => context.go('/cargo'), child: const Text('Post update')),
      ],
    ),
  );
}

class CargoCollectionRequestsPage extends StatelessWidget {
  const CargoCollectionRequestsPage({super.key});

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'COLLECTION',
    title: 'Collection requests',
    notificationRoute: '/cargo/notifications',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        const CustomerHeroCard(eyebrow: 'Collection', title: 'Pending collections', subtitle: 'Verify collection codes and hand over parcels to customers.'),
        const SizedBox(height: 20),
        Container(decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)), child: Column(children: [
          _reqRow(context, 'SAH-4829', 'Amina M.', '12 cartons', 'pending'),
          const Divider(height: 1, indent: 60),
          _reqRow(context, 'SAH-1204', 'Juma K.', '28 kg', 'ready'),
        ])),
      ],
    ),
  );

  Widget _reqRow(BuildContext context, String ref, String customer, String parcels, String status) => InkWell(
    onTap: () => context.push('/cargo/collection/verify'),
    child: Padding(padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14), child: Row(children: [
      Container(width: 40, height: 40, alignment: Alignment.center, decoration: BoxDecoration(color: brandCoral.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(10)), child: const Text('CL', style: TextStyle(color: brandCoral, fontWeight: FontWeight.w800))),
      const SizedBox(width: 14),
      Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('$ref · $customer', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
        const SizedBox(height: 2),
        Text(parcels, style: const TextStyle(color: appMuted, fontSize: 13)),
      ])),
      CustomerStatusPill(label: status),
    ])),
  );
}

class CargoConfirmHandoverPage extends StatelessWidget {
  const CargoConfirmHandoverPage({super.key});

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'COLLECTION',
    title: 'Confirm handover',
    notificationRoute: '/cargo/notifications',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        const CustomerHeroCard(eyebrow: 'Handover', title: 'Ready to hand over', subtitle: 'Confirm the parcels match and hand them to the customer.'),
        const SizedBox(height: 24),
        FilledButton(onPressed: () => context.go('/cargo'), child: const Text('Confirm handover')),
        const SizedBox(height: 12),
        OutlinedButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Cancel')),
      ],
    ),
  );
}

class CargoVerifyCollectionPage extends ConsumerStatefulWidget {
  const CargoVerifyCollectionPage({super.key});

  @override
  ConsumerState<CargoVerifyCollectionPage> createState() => _CargoVerifyCollectionPageState();
}

class _CargoVerifyCollectionPageState extends ConsumerState<CargoVerifyCollectionPage> {
  final _code = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _code.dispose();
    super.dispose();
  }

  Future<void> _verify() async {
    if (_code.text.trim().length < 4) return;
    setState(() => _busy = true);
    try {
      final isPin = RegExp(r'^[0-9]+$').hasMatch(_code.text.trim());
      final result = isPin
          ? await ref.read(warehouseAutomationRepositoryProvider).verifyCollection(pin: _code.text.trim())
          : await ref.read(warehouseAutomationRepositoryProvider).verifyCollection(code: _code.text.trim());
      if (result['valid'] == true || result['status'] == 'valid') {
        if (mounted) context.push('/cargo/collection/confirm');
      } else {
        if (mounted) context.push('/cargo/collection/code-used');
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'COLLECTION',
    title: 'Verify collection',
    notificationRoute: '/cargo/notifications',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        const CustomerHeroCard(eyebrow: 'Collection', title: 'Enter collection code', subtitle: 'Scan or enter the customer\'s collection code or PIN.'),
        const SizedBox(height: 24),
        TextField(controller: _code, decoration: const InputDecoration(labelText: 'Collection code or PIN'), keyboardType: TextInputType.text),
        const SizedBox(height: 24),
        FilledButton(onPressed: _busy ? null : _verify, child: Text(_busy ? 'Verifying...' : 'Verify')),
        const SizedBox(height: 12),
        OutlinedButton(onPressed: () => context.push('/cargo/collection/pin-entry'), child: const Text('Use PIN instead')),
      ],
    ),
  );
}

class CargoCollectionPinEntryPage extends ConsumerStatefulWidget {
  const CargoCollectionPinEntryPage({super.key});

  @override
  ConsumerState<CargoCollectionPinEntryPage> createState() => _CargoCollectionPinEntryPageState();
}

class _CargoCollectionPinEntryPageState extends ConsumerState<CargoCollectionPinEntryPage> {
  final _pin = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _pin.dispose();
    super.dispose();
  }

  Future<void> _verify() async {
    if (_pin.text.trim().length < 4) return;
    setState(() => _busy = true);
    try {
      await ref.read(warehouseAutomationRepositoryProvider).verifyCollection(pin: _pin.text.trim());
      if (mounted) context.push('/cargo/collection/confirm');
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'COLLECTION',
    title: 'PIN entry',
    notificationRoute: '/cargo/notifications',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        const CustomerHeroCard(eyebrow: 'Collection', title: 'Enter PIN', subtitle: 'Enter the 4–6 digit PIN shown to the customer.'),
        const SizedBox(height: 24),
        TextField(controller: _pin, decoration: const InputDecoration(labelText: 'PIN'), keyboardType: TextInputType.number, obscureText: true),
        const SizedBox(height: 24),
        FilledButton(onPressed: _busy ? null : _verify, child: Text(_busy ? 'Verifying...' : 'Verify PIN')),
      ],
    ),
  );
}

class CargoCollectionCodeUsedPage extends StatelessWidget {
  const CargoCollectionCodeUsedPage({super.key});

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'COLLECTION',
    title: 'Code already used',
    notificationRoute: '/cargo/notifications',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 28),
      children: [
        Column(children: [
          Container(width: 72, height: 72, decoration: BoxDecoration(color: appWarning.withValues(alpha: 0.15), shape: BoxShape.circle), child: const Icon(Icons.block, size: 40, color: appWarning)),
          const SizedBox(height: 20),
          const Text('Code already used', style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          const Text('This collection code has already been redeemed. Ask the customer for a fresh code.', textAlign: TextAlign.center, style: TextStyle(color: appMuted)),
        ]),
        const SizedBox(height: 24),
        FilledButton(onPressed: () => context.go('/cargo'), child: const Text('Continue')),
      ],
    ),
  );
}
