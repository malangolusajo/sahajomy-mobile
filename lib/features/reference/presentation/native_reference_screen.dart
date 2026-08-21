import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/ui/sahajomy_ui.dart';
import 'native_screen_specs.dart';

/// Native implementations for every HTML preview without a data-backed page.
/// The previews guide these widgets; no HTML is rendered by the application.
class PreviewPageLayout extends StatelessWidget {
  const PreviewPageLayout({required this.spec, super.key});

  final NativeScreenSpec spec;

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: SahajomyScreenHeader(role: spec.role, title: _headerTitle(spec)),
    body: switch (_kind(spec.fileName)) {
      _Kind.splash => _Splash(spec),
      _Kind.auth => _Auth(spec),
      _Kind.form => _Form(spec),
      _Kind.detail => _Detail(spec),
      _Kind.tracking => _Tracking(spec),
      _Kind.dashboard => _Dashboard(spec),
      _Kind.list => _List(spec),
    },
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
            'Every approved preview is available as native Flutter UI.',
          ),
          const SizedBox(height: 20),
          for (final group in groups.entries) ...[
            Text(group.key, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            _FlatList(
              children: [for (final spec in group.value) _row(context, spec)],
            ),
            const SizedBox(height: 20),
          ],
        ],
      ),
    );
  }

  Widget _row(BuildContext context, NativeScreenSpec spec) =>
      SahajomyPreviewRow(
        title: spec.title,
        subtitle: '${_kind(spec.fileName).name} screen',
        icon: _icon(spec),
        onTap: () => Navigator.pushNamed(context, spec.routeName),
      );
}

class _Dashboard extends StatelessWidget {
  const _Dashboard(this.spec);
  final NativeScreenSpec spec;

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.only(bottom: 24),
    children: [
      _Heading(spec),
      const SizedBox(height: 20),
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20),
        child: _Card(
          title: _metric(spec, true),
          subtitle: 'Open the live operational overview.',
          badge: 'Live',
          onTap: () => _toast(context, spec, 'Open overview'),
        ),
      ),
      const SizedBox(height: 12),
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20),
        child: _Card(
          title: _metric(spec, false),
          subtitle: 'Handle today\'s next action.',
          badge: 'Action',
          onTap: () => _toast(context, spec, 'Review activity'),
        ),
      ),
      const SizedBox(height: 20),
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20),
        child: FilledButton(
          onPressed: () => _toast(context, spec, _action(spec)),
          child: Text(_action(spec)),
        ),
      ),
    ],
  );
}

class _List extends StatelessWidget {
  const _List(this.spec);
  final NativeScreenSpec spec;

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.only(bottom: 24),
    children: [
      _Heading(spec),
      const SizedBox(height: 20),
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20),
        child: _FlatList(
          children: _rows(spec)
              .map(
                (row) => SahajomyPreviewRow(
                  title: row.$1,
                  subtitle: row.$2,
                  icon: _icon(spec),
                  trailing: SahajomyStatusPill(label: row.$3),
                  onTap: () => _toast(context, spec, row.$1),
                ),
              )
              .toList(),
        ),
      ),
      const SizedBox(height: 18),
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20),
        child: FilledButton(
          onPressed: () => _toast(context, spec, _action(spec)),
          child: Text(_action(spec)),
        ),
      ),
    ],
  );
}

class _Form extends StatefulWidget {
  const _Form(this.spec);
  final NativeScreenSpec spec;
  @override
  State<_Form> createState() => _FormState();
}

class _FormState extends State<_Form> {
  final _key = GlobalKey<FormState>();
  @override
  Widget build(BuildContext context) => Form(
    key: _key,
    child: ListView(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 24),
      children: [
        _Heading(widget.spec, padded: false),
        const SizedBox(height: 24),
        const Text(
          'COMPLETE THE DETAILS',
          style: TextStyle(
            color: brandCoral,
            fontSize: 10,
            fontWeight: FontWeight.w800,
            letterSpacing: 1.3,
          ),
        ),
        const SizedBox(height: 12),
        TextFormField(
          decoration: InputDecoration(labelText: _firstField(widget.spec)),
          validator: (value) => value == null || value.trim().isEmpty
              ? 'This field is required.'
              : null,
        ),
        const SizedBox(height: 14),
        TextFormField(
          decoration: InputDecoration(labelText: _secondField(widget.spec)),
        ),
        const SizedBox(height: 14),
        const TextField(
          minLines: 3,
          maxLines: 4,
          decoration: InputDecoration(labelText: 'Notes'),
        ),
        const SizedBox(height: 22),
        FilledButton(
          onPressed: () {
            if (_key.currentState!.validate()) {
              _toast(context, widget.spec, _action(widget.spec));
            }
          },
          child: Text(_action(widget.spec)),
        ),
      ],
    ),
  );
}

class _Detail extends StatelessWidget {
  const _Detail(this.spec);
  final NativeScreenSpec spec;
  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.fromLTRB(20, 20, 20, 24),
    children: [
      _Heading(spec, padded: false),
      const SizedBox(height: 20),
      Container(
        color: Colors.white,
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              _reference(spec),
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 4),
            const Text(
              'Current operational information',
              style: TextStyle(fontSize: 12, color: Color(0xFF64748B)),
            ),
            const SizedBox(height: 16),
            const Divider(),
            SahajomyKeyValueList(
              entries: {
                'status': 'Active',
                'updated': 'Today',
                'workspace': spec.role,
              },
            ),
          ],
        ),
      ),
      const SizedBox(height: 20),
      FilledButton(
        onPressed: () => _toast(context, spec, _action(spec)),
        child: Text(_action(spec)),
      ),
    ],
  );
}

class _Tracking extends StatelessWidget {
  const _Tracking(this.spec);
  final NativeScreenSpec spec;
  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.fromLTRB(20, 20, 20, 24),
    children: [
      _Heading(spec, padded: false),
      const SizedBox(height: 20),
      const TextField(
        decoration: InputDecoration(labelText: 'Tracking number'),
      ),
      const SizedBox(height: 20),
      const _Step('Booked', 'Shipment details confirmed', true),
      const _Step('In transit', 'Cargo is moving to destination', true),
      const _Step('Arriving', 'Warehouse update pending', false),
      const SizedBox(height: 16),
      FilledButton(
        onPressed: () => _toast(context, spec, 'Track shipment'),
        child: const Text('Track shipment'),
      ),
    ],
  );
}

class _Auth extends StatelessWidget {
  const _Auth(this.spec);
  final NativeScreenSpec spec;
  @override
  Widget build(BuildContext context) => Center(
    child: SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const SahajomyBrandMark(size: 72),
          const SizedBox(height: 28),
          Text(spec.title, style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 6),
          Text(_description(spec)),
          const SizedBox(height: 24),
          TextField(
            decoration: InputDecoration(
              labelText: spec.fileName.contains('otp')
                  ? 'Verification code'
                  : 'Phone number or email',
            ),
          ),
          if (spec.fileName.contains('register')) ...[
            const SizedBox(height: 14),
            const TextField(
              decoration: InputDecoration(labelText: 'Full name'),
            ),
          ],
          const SizedBox(height: 20),
          FilledButton(
            onPressed: () => _toast(context, spec, _action(spec)),
            child: Text(_action(spec)),
          ),
        ],
      ),
    ),
  );
}

class _Splash extends StatelessWidget {
  const _Splash(this.spec);
  final NativeScreenSpec spec;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.all(24),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Spacer(),
        const SahajomyBrandMark(size: 96),
        const SizedBox(height: 28),
        Text(spec.title, style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 8),
        Text(_description(spec)),
        const Spacer(),
        FilledButton(
          onPressed: () => _toast(context, spec, 'Get started'),
          child: const Text('Get started'),
        ),
        const SizedBox(height: 10),
        OutlinedButton(
          onPressed: () => _toast(context, spec, 'Sign in'),
          child: const Text('I already have an account'),
        ),
      ],
    ),
  );
}

class _Heading extends StatelessWidget {
  const _Heading(this.spec, {this.padded = true});
  final NativeScreenSpec spec;
  final bool padded;
  @override
  Widget build(BuildContext context) => Padding(
    padding: padded
        ? const EdgeInsets.fromLTRB(20, 20, 20, 0)
        : EdgeInsets.zero,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(spec.title, style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 5),
        Text(_description(spec)),
      ],
    ),
  );
}

class _FlatList extends StatelessWidget {
  const _FlatList({required this.children});
  final List<Widget> children;
  @override
  Widget build(BuildContext context) => Container(
    decoration: const BoxDecoration(
      color: Colors.white,
      border: Border.symmetric(vertical: BorderSide(color: Color(0xFFE2E8F0))),
    ),
    child: Column(children: children),
  );
}

class _Card extends StatelessWidget {
  const _Card({
    required this.title,
    required this.subtitle,
    required this.badge,
    required this.onTap,
  });
  final String title;
  final String subtitle;
  final String badge;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) => Material(
    color: Colors.white,
    borderRadius: BorderRadius.circular(16),
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          border: Border.all(color: const Color(0xFFE2E8F0)),
          borderRadius: BorderRadius.circular(16),
        ),
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
                    subtitle,
                    style: const TextStyle(
                      fontSize: 12,
                      color: Color(0xFF64748B),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            SahajomyStatusPill(label: badge),
          ],
        ),
      ),
    ),
  );
}

class _Step extends StatelessWidget {
  const _Step(this.title, this.subtitle, this.complete);
  final String title;
  final String subtitle;
  final bool complete;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 18),
    child: Row(
      children: [
        Icon(
          complete
              ? Icons.check_circle_rounded
              : Icons.radio_button_unchecked_rounded,
          color: complete ? brandCoral : const Color(0xFF94A3B8),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 2),
              Text(
                subtitle,
                style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

enum _Kind { splash, auth, dashboard, form, detail, tracking, list }

_Kind _kind(String name) {
  if (name == 'customer-splash.html') {
    return _Kind.splash;
  }
  if (name.contains('login') ||
      name.contains('register') ||
      name.contains('otp')) {
    return _Kind.auth;
  }
  if (name.contains('dashboard')) {
    return _Kind.dashboard;
  }
  if (name.contains('tracking') || name.contains('track-shipment')) {
    return _Kind.tracking;
  }
  if (name.contains('detail') ||
      name.contains('label') ||
      name.contains('collection-code') ||
      name.contains('booking-confirmation')) {
    return _Kind.detail;
  }
  if (name.contains('create-') ||
      name.contains('add-') ||
      name.contains('reserve-') ||
      name.contains('request') ||
      name.contains('feedback') ||
      name.contains('registration') ||
      name.contains('manual-intake')) {
    return _Kind.form;
  }
  return _Kind.list;
}

String _headerTitle(NativeScreenSpec spec) =>
    spec.title.length > 28 ? 'Details' : spec.title;
String _description(NativeScreenSpec spec) => switch (spec.role) {
  'Customer' =>
    'Review the latest shipping information and continue with confidence.',
  'Cargo Admin' =>
    'Keep cargo operations, documentation, and customer service on track.',
  'Sourcing Agent' =>
    'Manage batches, products, customer orders, and financial activity.',
  'Super Admin' =>
    'Review platform operations, governance, and access controls.',
  'Public' => 'Explore Sahajomy services, support, and shipping information.',
  _ => 'View the information securely shared with you.',
};
String _action(NativeScreenSpec spec) {
  final name = spec.fileName;
  if (name.contains('create') ||
      name.contains('add') ||
      name.contains('reserve') ||
      name.contains('request')) {
    return 'Continue';
  }
  if (name.contains('tracking')) {
    return 'Track shipment';
  }
  if (name.contains('login')) {
    return 'Send verification code';
  }
  if (name.contains('register')) {
    return 'Create account';
  }
  return switch (spec.role) {
    'Customer' => 'Continue',
    'Cargo Admin' => 'Open workspace',
    'Sourcing Agent' => 'Manage now',
    'Super Admin' => 'Review now',
    'Public' => 'Get started',
    _ => 'View details',
  };
}

String _metric(NativeScreenSpec spec, bool primary) => switch (spec.role) {
  'Customer' => primary ? '1 shipment in transit' : 'Reserve container space',
  'Cargo Admin' =>
    primary ? '4 containers need attention' : '12 pending reservations',
  'Sourcing Agent' =>
    primary ? '3 active sourcing batches' : '8 new customer orders',
  'Super Admin' => primary ? '12 user approvals' : 'Commission rate',
  _ => spec.title,
};
List<(String, String, String)> _rows(NativeScreenSpec spec) => [
  (
    ' ${spec.title} overview'.trim(),
    'Open the current ${spec.title.toLowerCase()} workflow.',
    'Live',
  ),
  ('Current status', 'Review the latest verified information.', 'Action'),
  ('History and documents', 'Keep the next operational step clear.', 'Ready'),
];
String _reference(NativeScreenSpec spec) => switch (spec.role) {
  'Customer' => 'MSKU 8392014',
  'Cargo Admin' => 'OPS-10482',
  'Sourcing Agent' => 'SO-10482',
  'Super Admin' => 'AUD-10482',
  _ => 'SAH-10482',
};
String _firstField(NativeScreenSpec spec) => spec.fileName.contains('reserve')
    ? 'Route or container'
    : spec.fileName.contains('product')
    ? 'Product name'
    : spec.fileName.contains('intake')
    ? 'Customer or shipment reference'
    : 'Name or reference';
String _secondField(NativeScreenSpec spec) => spec.fileName.contains('reserve')
    ? 'Volume (CBM)'
    : spec.fileName.contains('product')
    ? 'Price or minimum order'
    : spec.fileName.contains('intake')
    ? 'Warehouse'
    : 'Contact or destination';
IconData _icon(NativeScreenSpec spec) {
  final name = spec.fileName;
  if (name.contains('container') || name.contains('shipment')) {
    return Icons.inventory_2_outlined;
  }
  if (name.contains('document') ||
      name.contains('packing') ||
      name.contains('receipt')) {
    return Icons.description_outlined;
  }
  if (name.contains('notification') || name.contains('activity')) {
    return Icons.notifications_none_rounded;
  }
  if (name.contains('user') ||
      name.contains('customer') ||
      name.contains('agent')) {
    return Icons.people_outline_rounded;
  }
  if (name.contains('warehouse')) {
    return Icons.warehouse_outlined;
  }
  return Icons.arrow_outward_rounded;
}

void _toast(BuildContext context, NativeScreenSpec spec, String action) =>
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text('$action for ${spec.title}')));
