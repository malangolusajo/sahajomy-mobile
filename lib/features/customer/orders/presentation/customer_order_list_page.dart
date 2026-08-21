import 'package:flutter/material.dart';

import '../../../../core/ui/sahajomy_ui.dart';
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
      return ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
        children: [
          Text(
            'Your orders',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 6),
          const Text('Track sourcing and shipping orders from one place.'),
          const SizedBox(height: 20),
          for (final order in orders) ...[
            _OrderCard(order: order),
            const SizedBox(height: 12),
          ],
          const SizedBox(height: 8),
          FilledButton(
            onPressed: () {},
            child: const Text('Create sourcing request'),
          ),
        ],
      );
    },
  );
}

class _OrderCard extends StatelessWidget {
  const _OrderCard({required this.order});

  final Map<String, dynamic> order;

  @override
  Widget build(BuildContext context) {
    final itemCount = order['items_count'] ?? 0;
    final status = order['delivery_status'] as String? ?? 'Review';
    final reference = order['order_number'] ?? order['id'] ?? 'Agizisha order';

    return Card(
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
                    '$reference',
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '$itemCount item(s) · $status',
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
