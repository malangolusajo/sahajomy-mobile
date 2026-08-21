import 'package:flutter/material.dart';

import '../data/customer_shipments_repository.dart';

class ShipmentListPage extends StatefulWidget {
  const ShipmentListPage({super.key});
  @override
  State<ShipmentListPage> createState() => _ShipmentListPageState();
}

class _ShipmentListPageState extends State<ShipmentListPage> {
  final _repository = CustomerShipmentsRepository();
  late Future<List<Map<String, dynamic>>> _shipments = _repository
      .listShipmentOrders();

  void _retry() =>
      setState(() => _shipments = _repository.listShipmentOrders());

  @override
  Widget build(BuildContext context) =>
      FutureBuilder<List<Map<String, dynamic>>>(
        future: _shipments,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.error_outline, size: 44),
                    const SizedBox(height: 12),
                    const Text('Unable to load shipments.'),
                    const SizedBox(height: 12),
                    OutlinedButton(
                      onPressed: _retry,
                      child: const Text('Try again'),
                    ),
                  ],
                ),
              ),
            );
          }
          final shipments = snapshot.data ?? [];
          if (shipments.isEmpty) {
            return const Center(child: Text('No shipment orders yet.'));
          }
          return ListView.separated(
            padding: const EdgeInsets.all(20),
            itemCount: shipments.length,
            separatorBuilder: (_, _) => const SizedBox(height: 10),
            itemBuilder: (_, index) {
              final shipment = shipments[index];
              final reference =
                  shipment['order_number'] ?? shipment['id'] ?? 'Shipment';
              final status = shipment['status'] ?? 'Pending';
              return Card(
                child: ListTile(
                  title: Text(
                    '$reference',
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                  subtitle: Text('$status'),
                  trailing: const Icon(Icons.chevron_right),
                ),
              );
            },
          );
        },
      );
}
