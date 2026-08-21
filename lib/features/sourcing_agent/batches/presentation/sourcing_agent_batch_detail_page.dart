import 'package:flutter/material.dart';

import '../../../../core/ui/sahajomy_ui.dart';
import '../data/sourcing_agent_batches_repository.dart';
import 'sourcing_agent_batch_workflow_pages.dart';

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
    appBar: const SahajomyScreenHeader(
      role: 'Sourcing Agent',
      title: 'Batch details',
    ),
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
            Text(
              batch['title'] as String? ?? 'Sourcing batch',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 6),
            Text(
              batch['description'] as String? ??
                  'No description available for this batch.',
            ),
            const SizedBox(height: 20),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                SahajomyMetricTile(label: 'Orders', value: orders.length),
                SahajomyMetricTile(
                  label: 'Products',
                  value: batch['total_products'],
                ),
                SahajomyMetricTile(
                  label: 'Revenue',
                  value:
                      '${batch['currency'] ?? 'TZS'} ${batch['total_revenue'] ?? 0}',
                ),
              ],
            ),
            const SizedBox(height: 20),
            SahajomySectionCard(
              title: 'Quick actions',
              children: [
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    OutlinedButton.icon(
                      onPressed: () => Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => SourcingAgentAddProductPage(
                            batchId: widget.batchId,
                            batchTitle: batch['title'] as String?,
                          ),
                        ),
                      ),
                      icon: const Icon(Icons.add_box_outlined),
                      label: const Text('Add product'),
                    ),
                    OutlinedButton.icon(
                      onPressed: () => Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => SourcingAgentGenerateOrdersPage(
                            batchId: widget.batchId,
                            batchTitle: batch['title'] as String?,
                          ),
                        ),
                      ),
                      icon: const Icon(Icons.shopping_bag_outlined),
                      label: const Text('Orders'),
                    ),
                    OutlinedButton.icon(
                      onPressed: () => Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => SourcingAgentBatchFinancialsPage(
                            batchId: widget.batchId,
                          ),
                        ),
                      ),
                      icon: const Icon(Icons.payments_outlined),
                      label: const Text('Financials'),
                    ),
                    OutlinedButton.icon(
                      onPressed: () => Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => SourcingAgentPackingListCreatePage(
                            batchId: widget.batchId,
                            batchTitle: batch['title'] as String?,
                          ),
                        ),
                      ),
                      icon: const Icon(Icons.description_outlined),
                      label: const Text('Create packing list'),
                    ),
                  ],
                ),
              ],
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
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: () => Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => SourcingAgentOrderDetailPage(
                        batchTitle: batch['title'] as String?,
                        order: order,
                      ),
                    ),
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
