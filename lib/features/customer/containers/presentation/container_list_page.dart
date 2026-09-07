import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sahajomy_mobile/features/repository_providers.dart';

import '../../../../core/ui/sahajomy_ui.dart';
import '../../presentation/customer_components.dart';
import '../data/customer_containers_repository.dart';
import 'container_detail_page.dart';

class ContainerListPage extends ConsumerStatefulWidget {
  const ContainerListPage({super.key});
  @override
  ConsumerState<ContainerListPage> createState() => _ContainerListPageState();
}

class _ContainerListPageState extends ConsumerState<ContainerListPage> {
  String _query = '';
  CustomerContainersRepository get _repository =>
      ref.read(customerContainersRepositoryProvider);
  late Future<List<Map<String, dynamic>>> _items = Future.microtask(
    () => _repository.listContainers(),
  );
  void _retry() => setState(() => _items = _repository.listContainers());
  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Find container space',
    body: FutureBuilder<List<Map<String, dynamic>>>(
      future: _items,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return CustomerEmptyState(
            icon: Icons.error_outline,
            message: 'We could not load available containers.',
            actionLabel: 'Try again',
            onAction: _retry,
          );
        }
        final items = snapshot.data ?? [];
        if (items.isEmpty) {
          return const CustomerEmptyState(
            icon: Icons.inventory_2_outlined,
            message: 'No available containers right now.',
          );
        }
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          children: [
            const CustomerHeroCard(
              eyebrow: 'Sea freight',
              title: 'Find container space',
              subtitle: 'Search available sailings and book the volume your business needs.',
            ),
            const SizedBox(height: 24),
            TextField(
              onChanged: (value) => setState(() => _query = value.trim().toLowerCase()),
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search_rounded),
                hintText: 'Origin, destination, or container',
              ),
            ),
            const SizedBox(height: 16),
            for (final item in items.where((item) => '${item['origin']} ${item['destination']} ${item['operator']} ${item['container_size']}'.toLowerCase().contains(_query))) ...[
              _ContainerRow(item: item, onBooked: _retry),
              const SizedBox(height: 12),
            ],
          ],
        );
      },
    ),
  );
}

class _ContainerRow extends StatelessWidget {
  const _ContainerRow({required this.item, required this.onBooked});
  final Map<String, dynamic> item;
  final VoidCallback onBooked;
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
                    builder: (_) => ContainerDetailPage(container: item),
                  ),
                );
                if (created == true) onBooked();
              },
      ),
    );
  }
}
