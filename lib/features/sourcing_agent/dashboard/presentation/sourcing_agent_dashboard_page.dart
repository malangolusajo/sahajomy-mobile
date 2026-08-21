import 'package:flutter/material.dart';

import '../../../../core/ui/sahajomy_ui.dart';
import '../../batches/data/sourcing_agent_batches_repository.dart';
import '../../batches/presentation/sourcing_agent_batch_list_page.dart';
import '../../batches/presentation/sourcing_agent_batch_workflow_pages.dart';

class SourcingAgentDashboardPage extends StatefulWidget {
  const SourcingAgentDashboardPage({super.key});

  @override
  State<SourcingAgentDashboardPage> createState() =>
      _SourcingAgentDashboardPageState();
}

class _SourcingAgentDashboardPageState
    extends State<SourcingAgentDashboardPage> {
  final _repository = SourcingAgentBatchesRepository();
  late Future<Map<String, dynamic>> _batches = _repository.listBatches();

  void _retry() => setState(() => _batches = _repository.listBatches());

  @override
  Widget build(BuildContext context) => FutureBuilder<Map<String, dynamic>>(
    future: _batches,
    builder: (context, snapshot) {
      if (snapshot.connectionState != ConnectionState.done) {
        return const Center(child: CircularProgressIndicator());
      }
      if (snapshot.hasError) {
        return SahajomyMessageState(
          icon: Icons.wifi_off_rounded,
          message: 'Your sourcing overview is unavailable right now.',
          actionLabel: 'Try again',
          onAction: _retry,
        );
      }

      final batches = (snapshot.data!['batches'] as List? ?? const [])
          .cast<Map<String, dynamic>>();
      final activeBatches = batches
          .where((batch) => '${batch['status']}'.toLowerCase() != 'completed')
          .toList();
      final totalOrders = batches.fold<int>(
        0,
        (sum, batch) => sum + _asInt(batch['total_orders']),
      );
      return ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 24),
        children: [
          Text(
            'Your sourcing desk',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 6),
          const Text('Manage active batches, products, and customer orders.'),
          const SizedBox(height: 20),
          _DashboardActionCard(
            title: '${activeBatches.length} active sourcing batches',
            description: 'Open the live operational overview.',
            status: 'Live',
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => const SourcingAgentBatchListPage(),
              ),
            ),
          ),
          const SizedBox(height: 12),
          _DashboardActionCard(
            title: '$totalOrders new customer orders',
            description: 'Handle today\'s next action.',
            status: 'Action',
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) =>
                    SourcingAgentPackingListListPage(initialBatches: batches),
              ),
            ),
          ),
          const SizedBox(height: 20),
          FilledButton(
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => const SourcingAgentCreateBatchPage(),
              ),
            ),
            child: const Text('Create batch'),
          ),
        ],
      );
    },
  );
}

class _DashboardActionCard extends StatelessWidget {
  const _DashboardActionCard({
    required this.title,
    required this.description,
    required this.status,
    required this.onTap,
  });

  final String title;
  final String description;
  final String status;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Card(
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    description,
                    style: const TextStyle(fontSize: 12, height: 1.5),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            SahajomyStatusPill(label: status),
          ],
        ),
      ),
    ),
  );
}

int _asInt(Object? value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  return int.tryParse('$value') ?? 0;
}
