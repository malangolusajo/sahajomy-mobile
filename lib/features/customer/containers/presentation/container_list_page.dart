import 'package:flutter/material.dart';

import '../data/customer_containers_repository.dart';

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
  Widget build(
    BuildContext context,
  ) => FutureBuilder<List<Map<String, dynamic>>>(
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
        return const Center(child: Text('No available containers right now.'));
      }
      return ListView.separated(
        padding: const EdgeInsets.all(20),
        itemCount: items.length,
        separatorBuilder: (_, _) => const SizedBox(height: 10),
        itemBuilder: (_, index) {
          final item = items[index];
          return Card(
            child: ListTile(
              title: Text(
                '${item['container_number'] ?? item['name'] ?? 'Container'}',
                style: const TextStyle(fontWeight: FontWeight.w800),
              ),
              subtitle: Text(
                '${item['route'] ?? item['status'] ?? 'Available'}',
              ),
              trailing: const Icon(Icons.chevron_right),
            ),
          );
        },
      );
    },
  );
}
