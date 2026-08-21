import 'package:flutter/material.dart';

import '../data/super_admin_dashboard_repository.dart';

class SuperAdminDashboardPage extends StatefulWidget {
  const SuperAdminDashboardPage({super.key});
  @override
  State<SuperAdminDashboardPage> createState() =>
      _SuperAdminDashboardPageState();
}

class _SuperAdminDashboardPageState extends State<SuperAdminDashboardPage> {
  final _repository = SuperAdminDashboardRepository();
  late Future<Map<String, dynamic>> _overview = _repository.loadOverview();
  void _retry() => setState(() => _overview = _repository.loadOverview());
  @override
  Widget build(BuildContext context) => FutureBuilder<Map<String, dynamic>>(
    future: _overview,
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
      final data = snapshot.data!;
      return ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            'Platform oversight',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 6),
          const Text('Live governance metrics from Sahajomy operations.'),
          const SizedBox(height: 20),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              _Metric('Users', data['total_users']),
              _Metric('Approvals', data['pending_approvals']),
              _Metric('Operators', data['active_operators']),
              _Metric('Containers', data['total_containers']),
              _Metric('Reservations', data['total_reservations']),
              _Metric('Commission', '${data['current_commission_rate'] ?? 0}%'),
            ],
          ),
          const SizedBox(height: 24),
          Text(
            'Container status',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Text(
                (data['containers_by_status'] as Map? ?? const {}).entries
                    .map((entry) => '${entry.key}: ${entry.value}')
                    .join('\n'),
              ),
            ),
          ),
        ],
      );
    },
  );
}

class _Metric extends StatelessWidget {
  const _Metric(this.label, this.value);
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
            Text('$value', style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 4),
            Text(label),
          ],
        ),
      ),
    ),
  );
}
