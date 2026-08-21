import 'package:flutter/material.dart';

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
          final isAvailable =
              item['status'] != 'full' &&
              item['available_cbm'] is num &&
              (item['available_cbm'] as num) > 0;
          return Card(
            child: ListTile(
              title: Text(
                '${item['container_size'] ?? item['name'] ?? 'Container'}',
                style: const TextStyle(fontWeight: FontWeight.w800),
              ),
              subtitle: Text(
                '${item['origin'] ?? 'Origin'} to ${item['destination'] ?? 'Destination'}\n'
                '${item['available_cbm'] ?? 0} CBM available',
              ),
              trailing: Icon(
                isAvailable ? Icons.chevron_right : Icons.block_outlined,
              ),
              onTap: !isAvailable
                  ? null
                  : () async {
                      final created = await Navigator.push<bool>(
                        context,
                        MaterialPageRoute(
                          builder: (_) => ReserveContainerPage(container: item),
                        ),
                      );
                      if (created == true) _retry();
                    },
            ),
          );
        },
      );
    },
  );
}
