import 'package:flutter/material.dart';

import '../../../../core/ui/sahajomy_ui.dart';
import '../../reservations/presentation/reserve_container_page.dart';

class ContainerDetailPage extends StatelessWidget {
  const ContainerDetailPage({required this.container, super.key});
  final Map<String, dynamic> container;

  @override
  Widget build(BuildContext context) {
    final origin = container['origin'] ?? 'Origin';
    final destination = container['destination'] ?? 'Destination';
    final size =
        container['container_size'] ?? container['name'] ?? 'Container';
    final available = container['available_cbm'] ?? 0;
    final departure =
        container['departure_date'] ??
        container['departure'] ??
        'To be confirmed';
    return Scaffold(
      appBar: const SahajomyScreenHeader(
        role: 'Customer',
        title: 'Container details',
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
        children: [
          Text(
            '$destination bound',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 6),
          Text('$size · $origin to $destination · Departs $departure.'),
          const SizedBox(height: 20),
          Card(
            child: ListTile(
              title: Text(
                '${container['container_number'] ?? container['id'] ?? 'Container'}',
                style: const TextStyle(fontWeight: FontWeight.w800),
              ),
              subtitle: Text('$size · $origin → $destination'),
              trailing: const SahajomyStatusPill(label: 'Open'),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _Metric(
                  label: 'Available space',
                  value: '$available CBM',
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _Metric(label: 'Departure', value: '$departure'),
              ),
            ],
          ),
          const SizedBox(height: 20),
          FilledButton(
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => ReserveContainerPage(container: container),
              ),
            ),
            child: const Text('Reserve CBM'),
          ),
        ],
      ),
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric({required this.label, required this.value});
  final String label;
  final String value;
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      color: const Color(0xFFF1F5F9),
      borderRadius: BorderRadius.circular(12),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontSize: 12)),
        const SizedBox(height: 4),
        Text(
          value,
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
        ),
      ],
    ),
  );
}
