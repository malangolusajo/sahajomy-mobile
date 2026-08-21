import 'package:flutter/material.dart';

import '../data/sourcing_agent_batches_repository.dart';

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
      if (batches.isEmpty) {
        return const Center(child: Text('No sourcing batches yet.'));
      }
      return ListView.separated(
        padding: const EdgeInsets.all(20),
        itemCount: batches.length,
        separatorBuilder: (_, _) => const SizedBox(height: 12),
        itemBuilder: (_, index) {
          final batch = batches[index];
          return Card(
            child: ListTile(
              leading: const CircleAvatar(
                child: Icon(Icons.inventory_2_outlined),
              ),
              title: Text(
                batch['title'] as String? ?? 'Sourcing batch',
                style: const TextStyle(fontWeight: FontWeight.w800),
              ),
              subtitle: Text(
                '${batch['total_products'] ?? 0} products | ${batch['total_orders'] ?? 0} orders\n${batch['shipping_method'] ?? 'Shipping'} | ${batch['currency'] ?? 'TZS'} ${batch['shipping_fee_per_cbm'] ?? 0}/CBM',
              ),
              trailing: Chip(label: Text('${batch['status'] ?? 'Draft'}')),
            ),
          );
        },
      );
    },
  );
}
