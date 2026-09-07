import 'package:flutter/material.dart';
import '../../../reference/presentation/live_workflow_page.dart';
class ShipmentListPage extends StatelessWidget {
  const ShipmentListPage({super.key});
  @override
  Widget build(BuildContext context) => const LiveWorkflowPage(
    role: 'Customer', title: 'My shipments', endpoint: 'customer/shipment-orders/',
    description: 'Track cargo references, delivery status and shipment details.',
    embedded: true,
  );
}
