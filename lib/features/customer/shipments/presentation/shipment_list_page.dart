import 'package:flutter/material.dart';
import '../../presentation/customer_components.dart';
import '../../../reference/presentation/live_workflow_page.dart';
class ShipmentListPage extends StatelessWidget {
  const ShipmentListPage({super.key});
  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'My shipments',
    body: const LiveWorkflowPage(
      role: 'Customer', title: 'My shipments', endpoint: 'customer/shipment-orders/',
      description: 'Track cargo references, delivery status and shipment details.',
      embedded: true,
    ),
  );
}
