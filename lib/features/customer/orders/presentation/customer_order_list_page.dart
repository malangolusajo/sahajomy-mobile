import 'package:flutter/material.dart';
import '../../presentation/customer_components.dart';
import '../../../reference/presentation/live_workflow_page.dart';
class CustomerOrderListPage extends StatelessWidget {
  const CustomerOrderListPage({super.key});
  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Sourcing orders',
    body: const LiveWorkflowPage(
      role: 'Customer', title: 'Sourcing orders', endpoint: 'customer/orders',
      description: 'Review products, quantities and delivery progress for your sourcing orders.',
      actionLabel: 'Browse Agizisha products', actionRoute: '/agizisha', embedded: true,
    ),
  );
}
