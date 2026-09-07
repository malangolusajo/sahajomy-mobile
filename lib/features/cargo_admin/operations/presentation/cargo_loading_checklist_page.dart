import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../../../features/repository_providers.dart';
import '../../../customer/presentation/customer_components.dart';

class CargoLoadingChecklistPage extends ConsumerStatefulWidget {
  const CargoLoadingChecklistPage({required this.containerId, super.key});
  final String containerId;

  @override
  ConsumerState<CargoLoadingChecklistPage> createState() => _CargoLoadingChecklistPageState();
}

class _CargoLoadingChecklistPageState extends ConsumerState<CargoLoadingChecklistPage> {
  final _checks = <String, bool>{
    'All parcels received and inspected': false,
    'Packing list reviewed': false,
    'Container sealed and lock applied': false,
    'Customs documents attached': false,
  };
  bool _busy = false;

  Future<void> _depart() async {
    if (_busy || _checks.values.any((checked) => !checked)) return;
    setState(() => _busy = true);
    try {
      await ref.read(cargoOperationsRepositoryProvider).departContainer(widget.containerId);
      if (mounted) context.go('/cargo/containers/${widget.containerId}');
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('The container could not be marked departed.')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'CONTAINER', title: 'Loading checklist', notificationRoute: '/cargo/notifications',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        const CustomerHeroCard(eyebrow: 'Loading', title: 'Pre-departure checklist', subtitle: 'Confirm each physical step before recording departure.'),
        const SizedBox(height: 20),
        Container(
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)),
          child: Column(children: [
            for (final entry in _checks.entries) ...[
              CheckboxListTile(
                title: Text(entry.key), value: entry.value, activeColor: brandCoral,
                onChanged: _busy ? null : (value) => setState(() => _checks[entry.key] = value ?? false),
              ),
              if (entry.key != _checks.keys.last) const Divider(height: 1),
            ],
          ]),
        ),
        const SizedBox(height: 24),
        FilledButton.icon(
          onPressed: _checks.values.every((checked) => checked) && !_busy ? _depart : null,
          icon: const Icon(Icons.flight_takeoff),
          label: Text(_busy ? 'Recording departure…' : 'Mark container departed'),
        ),
      ],
    ),
  );
}
