import 'package:flutter/material.dart';

import '../../../../core/ui/sahajomy_ui.dart';
import '../../batches/data/sourcing_agent_batches_repository.dart';
import '../../batches/presentation/sourcing_agent_batch_workflow_pages.dart';

class SourcingAgentProductManagementPage extends StatefulWidget {
  const SourcingAgentProductManagementPage({super.key});

  @override
  State<SourcingAgentProductManagementPage> createState() =>
      _SourcingAgentProductManagementPageState();
}

class _SourcingAgentProductManagementPageState
    extends State<SourcingAgentProductManagementPage> {
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
          message: 'Products are unavailable right now.',
          actionLabel: 'Try again',
          onAction: _retry,
        );
      }

      final batches = (snapshot.data!['batches'] as List? ?? const [])
          .cast<Map<String, dynamic>>();
      return ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            'Product management',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 6),
          const Text(
            'Track which batches need product setup before customer orders can move forward.',
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
                for (final batch in batches) ...[
                  SahajomyPreviewRow(
                    title: batch['title'] as String? ?? 'Batch product',
                    subtitle:
                        '${batch['total_products'] ?? 0} products · ${batch['total_orders'] ?? 0} orders',
                    icon: Icons.inventory_2_outlined,
                    trailing: const SahajomyStatusPill(label: 'Active'),
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => SourcingAgentAddProductPage(
                          batchId: '${batch['id']}',
                          batchTitle: batch['title'] as String?,
                        ),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 18),
          FilledButton(
            onPressed: batches.isEmpty
                ? null
                : () => Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => SourcingAgentAddProductPage(
                        batchId: '${batches.first['id']}',
                        batchTitle: batches.first['title'] as String?,
                      ),
                    ),
                  ),
            child: const Text('Add product'),
          ),
          if (batches.isEmpty)
            const SahajomySectionCard(
              title: 'No batch catalogue yet',
              children: [Text('Create a batch first, then add products here.')],
            ),
        ],
      );
    },
  );
}
