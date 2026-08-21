import 'package:flutter/material.dart';

import '../data/customer_orders_repository.dart';

class CustomerOrderListPage extends StatefulWidget {
  const CustomerOrderListPage({super.key});

  @override
  State<CustomerOrderListPage> createState() => _CustomerOrderListPageState();
}

class _CustomerOrderListPageState extends State<CustomerOrderListPage> {
  final _repository = CustomerOrdersRepository();
  late Future<List<Map<String, dynamic>>> _orders = _repository.listOrders();

  void _retry() => setState(() => _orders = _repository.listOrders());

  @override
  Widget build(
    BuildContext context,
  ) => FutureBuilder<List<Map<String, dynamic>>>(
    future: _orders,
    builder: (context, snapshot) {
      if (snapshot.connectionState != ConnectionState.done) {
        return const Center(child: CircularProgressIndicator());
      }
      if (snapshot.hasError) {
        return _OrderMessage(
          message: 'We could not load your Agizisha orders.',
          actionLabel: 'Try again',
          onAction: _retry,
        );
      }
      final orders = snapshot.data ?? [];
      if (orders.isEmpty) {
        return const _OrderMessage(
          message:
              'No Agizisha orders yet. Your sourcing orders will appear here.',
        );
      }
      return ListView.separated(
        padding: const EdgeInsets.all(20),
        itemCount: orders.length,
        separatorBuilder: (_, _) => const SizedBox(height: 12),
        itemBuilder: (_, index) => _OrderCard(order: orders[index]),
      );
    },
  );
}

class _OrderCard extends StatelessWidget {
  const _OrderCard({required this.order});

  final Map<String, dynamic> order;

  @override
  Widget build(BuildContext context) {
    final currency = order['currency'] as String? ?? 'TZS';
    final amount = order['total_product_amount'];
    final total = amount is num ? amount.toStringAsFixed(0) : '$amount';
    final itemCount = order['items_count'] ?? 0;
    final status = order['delivery_status'] ?? 'Pending';

    return Card(
      child: ListTile(
        contentPadding: const EdgeInsets.all(16),
        leading: const CircleAvatar(child: Icon(Icons.shopping_bag_outlined)),
        title: Text(
          order['batch_title'] as String? ?? 'Agizisha order',
          style: const TextStyle(fontWeight: FontWeight.w800),
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Text('$itemCount item(s)  |  $currency $total\n$status'),
        ),
        trailing: const Icon(Icons.chevron_right),
      ),
    );
  }
}

class _OrderMessage extends StatelessWidget {
  const _OrderMessage({required this.message, this.actionLabel, this.onAction});

  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.shopping_bag_outlined, size: 44),
          const SizedBox(height: 14),
          Text(message, textAlign: TextAlign.center),
          if (onAction != null) ...[
            const SizedBox(height: 16),
            OutlinedButton(onPressed: onAction, child: Text(actionLabel!)),
          ],
        ],
      ),
    ),
  );
}
