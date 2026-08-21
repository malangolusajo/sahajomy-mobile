import 'package:flutter/material.dart';

import '../data/cargo_admin_containers_repository.dart';

class CargoAdminContainerListPage extends StatefulWidget {
  const CargoAdminContainerListPage({super.key});

  @override
  State<CargoAdminContainerListPage> createState() =>
      _CargoAdminContainerListPageState();
}

class _CargoAdminContainerListPageState
    extends State<CargoAdminContainerListPage> {
  final _repository = CargoAdminContainersRepository();
  late Future<List<Map<String, dynamic>>> _containers = _repository
      .listContainers();

  void _retry() => setState(() => _containers = _repository.listContainers());

  @override
  Widget build(BuildContext context) =>
      FutureBuilder<List<Map<String, dynamic>>>(
        future: _containers,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(
              child: OutlinedButton(
                onPressed: _retry,
                child: const Text('Try again'),
              ),
            );
          }
          final containers = snapshot.data ?? [];
          if (containers.isEmpty) {
            return const Center(
              child: Text('No containers have been created yet.'),
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.all(20),
            itemCount: containers.length,
            separatorBuilder: (_, _) => const SizedBox(height: 12),
            itemBuilder: (_, index) =>
                _ContainerCard(container: containers[index]),
          );
        },
      );
}

class _ContainerCard extends StatelessWidget {
  const _ContainerCard({required this.container});
  final Map<String, dynamic> container;

  @override
  Widget build(BuildContext context) {
    final fill = container['fill_percentage'];
    final value = fill is num ? fill.clamp(0, 100) / 100 : 0.0;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    container['reference'] as String? ?? 'Container',
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                ),
                Chip(label: Text('${container['status'] ?? 'Unknown'}')),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              '${container['warehouse_origin_name'] ?? 'Origin'} to ${container['warehouse_destination_name'] ?? 'Destination'}',
            ),
            const SizedBox(height: 12),
            LinearProgressIndicator(value: value),
            const SizedBox(height: 6),
            Text(
              '${container['reserved_cbm'] ?? 0} / ${container['max_cbm'] ?? 0} CBM reserved | ${container['available_cbm'] ?? 0} CBM free',
            ),
          ],
        ),
      ),
    );
  }
}
