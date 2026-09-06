import 'package:flutter/material.dart';

import '../../../core/ui/sahajomy_ui.dart';
import '../../../shared/presentation/feature_menu_page.dart';
import '../../reference/presentation/live_workflow_page.dart';
import '../batches/presentation/sourcing_agent_batch_list_page.dart';
import '../dashboard/presentation/sourcing_agent_dashboard_page.dart';

class SourcingAgentShell extends StatefulWidget {
  const SourcingAgentShell({super.key});
  @override
  State<SourcingAgentShell> createState() => _SourcingAgentShellState();
}

class _SourcingAgentShellState extends State<SourcingAgentShell> {
  var _index = 0;
  static const _titles = ['Home', 'Batches', 'Orders', 'More'];
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
        LiveWorkflowPage(
          role: 'Sourcing Agent',
          title: 'Agizisha orders',
          endpoint: 'sourcing_agent/agizisha-orders',
        ),
        _SourcingAgentMorePage(),
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
          label: 'Orders',
          icon: Icons.shopping_bag_outlined,
        ),
        SahajomyNavigationDestination(
          label: 'More',
          icon: Icons.more_horiz_rounded,
        ),
      ],
    ),
  );
}

class _SourcingAgentMorePage extends StatelessWidget {
  const _SourcingAgentMorePage();

  @override
  Widget build(BuildContext context) => const FeatureMenuPage(
    title: 'Sourcing operations',
    description: 'Manage your storefront, cargo, documents, and earnings.',
    entries: [
      FeatureMenuEntry(
        title: 'Storefront',
        subtitle: 'Manage the public agent catalogue.',
        icon: Icons.storefront_outlined,
        route: '/agent/agizisha-storefront',
      ),
      FeatureMenuEntry(
        title: 'Products',
        subtitle: 'Add and manage sourcing products.',
        icon: Icons.inventory_outlined,
        route: '/reference/agent-product-management',
      ),
      FeatureMenuEntry(
        title: 'Packing lists',
        subtitle: 'Create and review batch packing lists.',
        icon: Icons.description_outlined,
        route: '/agent/packing-lists',
      ),
      FeatureMenuEntry(
        title: 'Financials',
        subtitle: 'Income, commissions, and batch totals.',
        icon: Icons.account_balance_wallet_outlined,
        route: '/agent/financials',
      ),
      FeatureMenuEntry(
        title: 'Sea bookings',
        subtitle: 'Track sea freight reservations.',
        icon: Icons.directions_boat_outlined,
        route: '/agent/sea-bookings',
      ),
      FeatureMenuEntry(
        title: 'Express Air Cargo',
        subtitle: 'Create and manage air cargo bookings.',
        icon: Icons.flight_outlined,
        route: '/agent/express-air-cargo',
      ),
      FeatureMenuEntry(
        title: 'China addresses',
        subtitle: 'View provider-scoped forwarding addresses.',
        icon: Icons.location_on_outlined,
        route: '/agent/china-addresses',
      ),
      FeatureMenuEntry(
        title: 'Containers',
        subtitle: 'Browse and reserve available capacity.',
        icon: Icons.inventory_2_outlined,
        route: '/agent/containers',
      ),
      FeatureMenuEntry(
        title: 'Reservations',
        subtitle: 'Review active space reservations.',
        icon: Icons.event_available_outlined,
        route: '/reference/agent-reservations',
      ),
      FeatureMenuEntry(
        title: 'Tracking',
        subtitle: 'Follow sourcing shipment milestones.',
        icon: Icons.route_outlined,
        route: '/agent/track-shipments',
      ),
      FeatureMenuEntry(
        title: 'Notifications',
        subtitle: 'Review batch and order activity.',
        icon: Icons.notifications_outlined,
        route: '/reference/agent-notifications',
      ),
    ],
  );
}
