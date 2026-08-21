import 'package:flutter/material.dart';

import '../../../core/ui/sahajomy_ui.dart';
import '../batches/presentation/sourcing_agent_batch_list_page.dart';
import '../dashboard/presentation/sourcing_agent_dashboard_page.dart';
import '../notifications/presentation/sourcing_agent_notifications_page.dart';
import '../products/presentation/sourcing_agent_product_management_page.dart';

class SourcingAgentShell extends StatefulWidget {
  const SourcingAgentShell({super.key});
  @override
  State<SourcingAgentShell> createState() => _SourcingAgentShellState();
}

class _SourcingAgentShellState extends State<SourcingAgentShell> {
  var _index = 0;
  static const _titles = ['Home', 'Batches', 'Products', 'Alerts'];
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: SahajomyWorkspaceHeader(
      role: 'Sourcing Agent',
      title: _titles[_index],
    ),
    body: IndexedStack(
      index: _index,
      children: const [
        SourcingAgentDashboardPage(),
        SourcingAgentBatchListPage(),
        SourcingAgentProductManagementPage(),
        SourcingAgentNotificationsPage(),
      ],
    ),
    bottomNavigationBar: SahajomyPreviewNavigation(
      selectedIndex: _index,
      onSelected: (value) => setState(() => _index = value),
      destinations: const [
        SahajomyNavigationDestination(label: 'Home', icon: Icons.home_outlined),
        SahajomyNavigationDestination(
          label: 'Batches',
          icon: Icons.inventory_2_outlined,
        ),
        SahajomyNavigationDestination(
          label: 'Products',
          icon: Icons.inventory_outlined,
        ),
        SahajomyNavigationDestination(
          label: 'Alerts',
          icon: Icons.notifications_none_rounded,
        ),
      ],
    ),
  );
}
