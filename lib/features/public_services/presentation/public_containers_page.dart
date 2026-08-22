import 'package:flutter/material.dart';

import '../../../core/ui/sahajomy_ui.dart';
import '../data/public_services_repository.dart';

class PublicContainersPage extends StatefulWidget {
  const PublicContainersPage({super.key});

  @override
  State<PublicContainersPage> createState() => _PublicContainersPageState();
}

class _PublicContainersPageState extends State<PublicContainersPage> {
  final _repository = PublicServicesRepository();
  late Future<List<Map<String, dynamic>>> _containers = _repository
      .listContainers();

  void _retry() => setState(() => _containers = _repository.listContainers());

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(role: 'Public', title: 'Containers'),
    body: FutureBuilder<List<Map<String, dynamic>>>(
      future: _containers,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return SahajomyMessageState(
            icon: Icons.wifi_off_rounded,
            message: 'Available containers are unavailable right now.',
            actionLabel: 'Try again',
            onAction: _retry,
          );
        }
        final containers = snapshot.data!;
        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              'Available containers',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 6),
            const Text('Find open container space for your next shipment.'),
            const SizedBox(height: 20),
            if (containers.isEmpty)
              const SahajomySectionCard(
                title: 'No open containers',
                children: [
                  Text('Check back soon for the next available route.'),
                ],
              ),
            for (final container in containers) ...[
              SahajomyPreviewRow(
                title:
                    '${container['reference'] ?? container['container_number'] ?? 'Container'}',
                subtitle:
                    '${container['origin'] ?? container['warehouse_origin_name'] ?? 'Origin'} to ${container['destination'] ?? container['warehouse_destination_name'] ?? 'Destination'} · ${container['available_cbm'] ?? 0} CBM available',
                icon: Icons.inventory_2_outlined,
                trailing: SahajomyStatusPill(
                  label: '${container['status'] ?? 'Available'}',
                ),
                onTap: () => ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Sign in to reserve container space.'),
                  ),
                ),
              ),
              const SizedBox(height: 8),
            ],
          ],
        );
      },
    ),
  );
}
