import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sahajomy_mobile/features/repository_providers.dart';

import '../data/cargo_admin_dashboard_repository.dart';

class CargoAdminDashboardPage extends ConsumerStatefulWidget {
  const CargoAdminDashboardPage({super.key});

  @override
  ConsumerState<CargoAdminDashboardPage> createState() =>
      _CargoAdminDashboardPageState();
}

class _CargoAdminDashboardPageState
    extends ConsumerState<CargoAdminDashboardPage> {
  CargoAdminDashboardRepository get _repository =>
      ref.read(cargoAdminDashboardRepositoryProvider);
  late Future<Map<String, dynamic>> _dashboard = Future.microtask(
    () => _repository.loadDashboard(),
  );

  void _retry() => setState(() => _dashboard = _repository.loadDashboard());

  @override
  Widget build(BuildContext context) => FutureBuilder<Map<String, dynamic>>(
    future: _dashboard,
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
      final dashboard = snapshot.data!;
      final actions = (dashboard['pending_actions'] as List? ?? const [])
          .cast<Map<String, dynamic>>();
      return ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            'Operations overview',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 6),
          const Text('Live workload for your cargo operations.'),
          const SizedBox(height: 20),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              _Metric(
                label: 'Active containers',
                value: dashboard['active_containers'],
              ),
              _Metric(
                label: 'Bookings',
                value: dashboard['total_reservations'],
              ),
              _Metric(
                label: 'Pending payments',
                value: dashboard['pending_payments'],
              ),
              _Metric(
                label: 'Air cargo queue',
                value: dashboard['pending_air_bookings'],
              ),
            ],
          ),
          const SizedBox(height: 24),
          Text(
            'Pending actions',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          if (actions.isEmpty)
            const Text('No operational actions are waiting.'),
          ...actions.map(
            (action) => Card(
              child: ListTile(
                leading: const Icon(Icons.task_alt_outlined),
                title: Text(action['label'] as String? ?? 'Action'),
                trailing: Chip(label: Text('${action['count'] ?? 0}')),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: ListTile(
              leading: const Icon(Icons.inventory_2_outlined),
              title: const Text('Booked capacity'),
              subtitle: Text(
                '${dashboard['total_reserved_cbm'] ?? 0} CBM booked across your containers.',
              ),
            ),
          ),
        ],
      );
    },
  );
}

class _Metric extends StatelessWidget {
  const _Metric({required this.label, required this.value});
  final String label;
  final Object? value;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: 164,
    child: Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${value ?? 0}',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 4),
            Text(label),
          ],
        ),
      ),
    ),
  );
}
