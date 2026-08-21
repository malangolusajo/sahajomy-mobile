import 'package:flutter/material.dart';

import '../../../../core/ui/sahajomy_ui.dart';
import '../data/customer_containers_repository.dart';
import '../../reservations/presentation/reserve_container_page.dart';

class ContainerListPage extends StatefulWidget {
  const ContainerListPage({super.key});
  @override
  State<ContainerListPage> createState() => _ContainerListPageState();
}

class _ContainerListPageState extends State<ContainerListPage> {
  final _repository = CustomerContainersRepository();
  late Future<List<Map<String, dynamic>>> _items = _repository.listContainers();
  void _retry() => setState(() => _items = _repository.listContainers());
  @override
  Widget build(BuildContext context) =>
      FutureBuilder<List<Map<String, dynamic>>>(
        future: _items,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(
              child: OutlinedButton(
                onPressed: _retry,
                child: const Text('Retry containers'),
              ),
            );
          }
          final items = snapshot.data ?? [];
          if (items.isEmpty) {
            return const Center(
              child: Text('No available containers right now.'),
            );
          }
          return ListView(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
            children: [
              Text(
                'Find container space',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 6),
              const Text(
                'Search available sailings and reserve the volume your business needs.',
              ),
              const SizedBox(height: 20),
              const TextField(
                decoration: InputDecoration(
                  prefixIcon: Icon(Icons.search_rounded),
                  hintText: 'Origin, destination, or container',
                ),
              ),
              const SizedBox(height: 16),
              for (final item in items) ...[
                _ContainerRow(item: item, onReserved: _retry),
                const SizedBox(height: 12),
              ],
              FilledButton(
                onPressed: () {},
                child: const Text('Search containers'),
              ),
            ],
          );
        },
      );
}

class _ContainerRow extends StatelessWidget {
  const _ContainerRow({required this.item, required this.onReserved});
  final Map<String, dynamic> item;
  final VoidCallback onReserved;
  @override
  Widget build(BuildContext context) {
    final available =
        item['status'] != 'full' &&
        item['available_cbm'] is num &&
        (item['available_cbm'] as num) > 0;
    return Card(
      child: ListTile(
        title: Text(
          '${item['origin'] ?? 'Origin'} → ${item['destination'] ?? 'Destination'}',
          style: const TextStyle(fontWeight: FontWeight.w800),
        ),
        subtitle: Text(
          '${item['container_size'] ?? item['name'] ?? 'Container'} · ${item['available_cbm'] ?? 0} CBM available',
        ),
        trailing: SahajomyStatusPill(label: available ? 'Available' : 'Full'),
        onTap: !available
            ? null
            : () async {
                final created = await Navigator.push<bool>(
                  context,
                  MaterialPageRoute(
                    builder: (_) => ReserveContainerPage(container: item),
                  ),
                );
                if (created == true) onReserved();
              },
      ),
    );
  }
}
