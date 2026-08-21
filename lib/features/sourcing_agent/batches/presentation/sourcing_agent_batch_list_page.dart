import 'package:flutter/material.dart';

import '../../../../core/ui/sahajomy_ui.dart';
import '../data/sourcing_agent_batches_repository.dart';
import 'sourcing_agent_batch_detail_page.dart';
import 'sourcing_agent_batch_workflow_pages.dart';

class SourcingAgentBatchListPage extends StatefulWidget {
  const SourcingAgentBatchListPage({super.key});
  @override
  State<SourcingAgentBatchListPage> createState() =>
      _SourcingAgentBatchListPageState();
}

class _SourcingAgentBatchListPageState
    extends State<SourcingAgentBatchListPage> {
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
        return Center(
          child: OutlinedButton(
            onPressed: _retry,
            child: const Text('Try again'),
          ),
        );
      }
      final batches = (snapshot.data!['batches'] as List? ?? const [])
          .cast<Map<String, dynamic>>();
      return ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            'Sourcing batches',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 6),
          const Text(
            'Open a live batch, review its orders, and move it toward packing-list readiness.',
          ),
          const SizedBox(height: 20),
          Container(
            decoration: const BoxDecoration(
              color: Colors.white,
              border: Border.symmetric(
                vertical: BorderSide(color: Color(0xFFE2E8F0)),
              ),
            ),
            child: Column(
              children: [
                for (final batch in batches)
                  SahajomyPreviewRow(
                    title: batch['title'] as String? ?? 'Sourcing batch',
                    subtitle:
                        '${batch['total_orders'] ?? 0} orders · ${batch['shipping_method'] ?? 'Shipping'} · ${batch['status'] ?? 'Draft'}',
                    icon: Icons.inventory_2_outlined,
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => SourcingAgentBatchDetailPage(
                          batchId: batch['id'] as String,
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
          if (batches.isNotEmpty) const SizedBox(height: 18),
          FilledButton(
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => const SourcingAgentCreateBatchPage(),
              ),
            ),
            child: const Text('Create batch'),
          ),
          const SizedBox(height: 18),
          if (batches.isEmpty)
            const SahajomySectionCard(
              title: 'No sourcing batches yet',
              children: [
                Text(
                  'Create the first batch to start collecting products and customer orders.',
                ),
              ],
            ),
        ],
      );
    },
  );
}
