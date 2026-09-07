import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../../../features/repository_providers.dart';
import '../../../customer/presentation/customer_components.dart';

class CargoContainersPage extends ConsumerStatefulWidget {
  const CargoContainersPage({super.key});

  @override
  ConsumerState<CargoContainersPage> createState() => _CargoContainersPageState();
}

class _CargoContainersPageState extends ConsumerState<CargoContainersPage> {
  late Future<List<Map<String, dynamic>>> _containers;

  @override
  void initState() {
    super.initState();
    _containers = ref.read(cargoOperationsRepositoryProvider).listContainers();
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'CARGO COMPANY',
    title: 'Cargo · Containers',
    notificationRoute: '/cargo/notifications',
    floatingActionButton: FloatingActionButton.extended(
      onPressed: () => context.push('/cargo/containers/new'),
      icon: const Icon(Icons.add),
      label: const Text('New container'),
    ),
    body: RefreshIndicator(
      onRefresh: () async {
        setState(() {
          _containers = ref.read(cargoOperationsRepositoryProvider).listContainers();
        });
        await _containers;
      },
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 100),
        children: [
          const CustomerHeroCard(
            eyebrow: 'Container fleet',
            title: 'Active containers',
            subtitle: 'Track capacity, fill level, and lifecycle for every container you operate.',
          ),
          const SizedBox(height: 20),
          FutureBuilder<List<Map<String, dynamic>>>(
            future: _containers,
            builder: (context, snapshot) {
              if (snapshot.connectionState != ConnectionState.done) {
                return const CustomerSkeletonList(count: 5);
              }
              if (snapshot.hasError) {
                return CustomerEmptyState(
                  icon: Icons.error_outline,
                  message: 'Could not load containers.',
                  actionLabel: 'Retry',
                  onAction: () => setState(() {
                    _containers = ref.read(cargoOperationsRepositoryProvider).listContainers();
                  }),
                );
              }
              final list = snapshot.data ?? [];
              if (list.isEmpty) {
                return const CustomerEmptyState(
                  icon: Icons.inventory_2_outlined,
                  message: 'No containers yet. Create one to start accepting bookings.',
                );
              }
              return Column(
                children: [
                  for (final c in list) _containerCard(c),
                ],
              );
            },
          ),
        ],
      ),
    ),
  );

  Widget _containerCard(Map<String, dynamic> c) {
    final fill = (c['fill_percentage'] ?? 0).toDouble();
    final size = c['container_size'] ?? '40ft';
    final status = c['status'] ?? 'draft';
    final origin = c['warehouse_origin_name'] ?? 'Origin';
    final dest = c['warehouse_destination_name'] ?? 'Destination';
    return GestureDetector(
      onTap: () => context.push('/cargo/containers/${c['id']}'),
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: appBorder),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 44, height: 44, alignment: Alignment.center,
                  decoration: BoxDecoration(color: brandGold.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(12)),
                  child: Text(size, style: const TextStyle(color: brandGold, fontWeight: FontWeight.w800, fontSize: 11)),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(c['reference'] ?? 'Container', style: const TextStyle(fontWeight: FontWeight.w800, fontFamily: 'monospace')),
                      const SizedBox(height: 2),
                      Text('$origin → $dest', style: const TextStyle(color: appMuted, fontSize: 13)),
                    ],
                  ),
                ),
                CustomerStatusPill(label: status.toString().replaceAll('_', ' ')),
              ],
            ),
            const SizedBox(height: 14),
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: LinearProgressIndicator(
                value: (fill / 100).clamp(0.0, 1.0),
                minHeight: 8,
                backgroundColor: appBorder,
                valueColor: const AlwaysStoppedAnimation(brandCoral),
              ),
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('${c['reserved_cbm'] ?? 0} / ${c['max_cbm'] ?? 0} CBM filled', style: const TextStyle(color: appMuted, fontSize: 12)),
                Text('$fill%', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12)),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
