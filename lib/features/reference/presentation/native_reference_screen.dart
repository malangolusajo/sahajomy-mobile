import 'package:flutter/material.dart';

import '../../../core/ui/sahajomy_ui.dart';
import 'native_screen_specs.dart';

class NativeReferenceScreen extends StatelessWidget {
  const NativeReferenceScreen({required this.spec, super.key});

  final NativeScreenSpec spec;

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: SahajomyScreenHeader(
      role: spec.role,
      title: _shortTitle(spec.title),
    ),
    body: SafeArea(
      top: false,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
        children: [
          Text(spec.title, style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 6),
          Text(_description(spec)),
          const SizedBox(height: 20),
          _ActionRow(
            title: _primaryAction(spec),
            description:
                'Review the latest information and continue your workflow.',
            status: 'Live',
          ),
          const SizedBox(height: 12),
          _ActionRow(
            title: 'Current status',
            description: 'Details are organized here for a clear next action.',
            status: 'Action',
          ),
          const SizedBox(height: 20),
          FilledButton(onPressed: () {}, child: Text(_primaryAction(spec))),
          const SizedBox(height: 28),
          const _PrototypeStates(),
        ],
      ),
    ),
  );
}

class NativeScreenCatalog extends StatelessWidget {
  const NativeScreenCatalog({super.key});

  @override
  Widget build(BuildContext context) {
    final groups = <String, List<NativeScreenSpec>>{};
    for (final spec in nativeScreenSpecs) {
      (groups[spec.role] ??= []).add(spec);
    }
    return Scaffold(
      appBar: const SahajomyScreenHeader(
        role: 'Sahajomy',
        title: 'All screens',
        showBack: false,
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
        children: [
          Text(
            'Native screen library',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 6),
          const Text(
            'Every approved screen is available as native Flutter UI.',
          ),
          const SizedBox(height: 20),
          for (final entry in groups.entries) ...[
            Text(entry.key, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Card(
              child: Column(
                children: [
                  for (final spec in entry.value)
                    ListTile(
                      title: Text(spec.title),
                      trailing: const Icon(Icons.chevron_right_rounded),
                      onTap: () => Navigator.pushNamed(context, spec.routeName),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 20),
          ],
        ],
      ),
    );
  }
}

class _ActionRow extends StatelessWidget {
  const _ActionRow({
    required this.title,
    required this.description,
    required this.status,
  });

  final String title;
  final String description;
  final String status;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 4),
                Text(
                  description,
                  style: const TextStyle(fontSize: 12, height: 1.5),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          SahajomyStatusPill(label: status),
        ],
      ),
    ),
  );
}

class _PrototypeStates extends StatelessWidget {
  const _PrototypeStates();

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      color: Colors.white,
      border: Border.all(color: const Color(0xFFE2E8F0)),
      borderRadius: BorderRadius.circular(12),
    ),
    child: const Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'PROTOTYPE STATES',
          style: TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w800,
            letterSpacing: 1,
            color: Color(0xFF94A3B8),
          ),
        ),
        SizedBox(height: 8),
        Wrap(
          spacing: 8,
          children: [
            Chip(label: Text('Loading')),
            Chip(label: Text('Empty')),
            Chip(label: Text('Error')),
          ],
        ),
      ],
    ),
  );
}

String _shortTitle(String title) => title.length > 28 ? 'Details' : title;

String _description(NativeScreenSpec spec) => switch (spec.role) {
  'Customer' =>
    'Manage your shipping, orders, reservations, and collection activity.',
  'Cargo Admin' =>
    'Keep operational work, documentation, and cargo handling on track.',
  'Sourcing Agent' =>
    'Manage batches, products, customer orders, and financial activity.',
  'Super Admin' =>
    'Review platform operations, access, and governance activity.',
  'Public' => 'Explore Sahajomy services, support, and shipping information.',
  _ => 'View the information shared securely with you.',
};

String _primaryAction(NativeScreenSpec spec) => switch (spec.role) {
  'Customer' => 'Continue',
  'Cargo Admin' => 'Open workspace',
  'Sourcing Agent' => 'Manage now',
  'Super Admin' => 'Review now',
  'Public' => 'Get started',
  _ => 'View details',
};
