import 'package:flutter/material.dart';

import '../data/sourcing_agent_batches_repository.dart';

class SourcingAgentBatchDetailPage extends StatefulWidget {
  const SourcingAgentBatchDetailPage({super.key, required this.batchId});
  final String batchId;
  @override
  State<SourcingAgentBatchDetailPage> createState() =>
      _SourcingAgentBatchDetailPageState();
}

class _SourcingAgentBatchDetailPageState
    extends State<SourcingAgentBatchDetailPage> {
  final _repository = SourcingAgentBatchesRepository();
  late Future<List<Map<String, dynamic>>> _data = _load();
  Future<List<Map<String, dynamic>>> _load() => Future.wait([
    _repository.getBatch(widget.batchId),
    _repository.listOrders(widget.batchId),
  ]);
  void _retry() => setState(() => _data = _load());

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Batch details')),
    body: FutureBuilder<List<Map<String, dynamic>>>(
      future: _data,
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
        final batch = snapshot.data![0];
        final orders = (snapshot.data![1]['orders'] as List? ?? const [])
            .cast<Map<String, dynamic>>();
        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      batch['title'] as String? ?? 'Sourcing batch',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 8),
                    Text(batch['description'] as String? ?? 'No description.'),
                    const SizedBox(height: 12),
                    Text(
                      '${batch['currency'] ?? 'TZS'} ${batch['total_revenue'] ?? 0} revenue | ${batch['order_count'] ?? 0} orders',
                    ),
                    Text(
                      '${batch['currency'] ?? 'TZS'} ${batch['net_earnings'] ?? 0} net earnings',
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 20),
            Text('Orders', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            if (orders.isEmpty) const Text('No orders in this batch yet.'),
            ...orders.map(
              (order) => Card(
                child: ListTile(
                  leading: const Icon(Icons.shopping_bag_outlined),
                  title: Text(order['order_reference'] as String? ?? 'Order'),
                  subtitle: Text(
                    '${order['customer_name'] ?? 'Customer'} | ${order['payment_status'] ?? 'Pending'} | ${order['delivery_status'] ?? 'Pending'}',
                  ),
                ),
              ),
            ),
          ],
        );
      },
    ),
  );
}
