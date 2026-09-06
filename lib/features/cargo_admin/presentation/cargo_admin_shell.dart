import 'package:flutter/material.dart';

import '../../../core/ui/sahajomy_ui.dart';
import '../../../shared/presentation/feature_menu_page.dart';
import '../../reference/presentation/live_workflow_page.dart';
import '../containers/presentation/cargo_admin_container_list_page.dart';
import '../documents/presentation/cargo_admin_documentation_workspace_page.dart';

class CargoAdminShell extends StatefulWidget {
  const CargoAdminShell({super.key});

  @override
  State<CargoAdminShell> createState() => _CargoAdminShellState();
}

class _CargoAdminShellState extends State<CargoAdminShell> {
  var _index = 0;
  static const _titles = ['Bookings', 'Containers', 'Receipts', 'Account'];

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: SahajomyWorkspaceHeader(
      role: 'Cargo Admin',
      title: _titles[_index],
    ),
    body: IndexedStack(
      index: _index,
      children: const [
        LiveWorkflowPage(
          role: 'Cargo Admin',
          title: 'Bookings',
          endpoint: 'cargo_admin/reservations',
        ),
        CargoAdminContainerListPage(),
        CargoAdminReceiptsPage(),
        _CargoAdminMorePage(),
      ],
    ),
    bottomNavigationBar: SahajomyPreviewNavigation(
      selectedIndex: _index,
      onSelected: (value) => setState(() => _index = value),
      destinations: const [
        SahajomyNavigationDestination(
          label: 'Bookings',
          icon: Icons.event_available_outlined,
        ),
        SahajomyNavigationDestination(
          label: 'Containers',
          icon: Icons.inventory_2_outlined,
        ),
        SahajomyNavigationDestination(
          label: 'Receipts',
          icon: Icons.receipt_long_outlined,
        ),
        SahajomyNavigationDestination(
          label: 'Account',
          icon: Icons.person_outline_rounded,
        ),
      ],
    ),
  );
}

class _CargoAdminMorePage extends StatelessWidget {
  const _CargoAdminMorePage();

  @override
  Widget build(BuildContext context) => const FeatureMenuPage(
    title: 'Cargo operations',
    description: 'Manage company operations, people, billing, and documents.',
    entries: [
      FeatureMenuEntry(
        title: 'Dashboard',
        subtitle: 'Warehouse metrics and operational alerts.',
        icon: Icons.dashboard_outlined,
        route: '/cargo/dashboard',
      ),
      FeatureMenuEntry(
        title: 'Warehouses',
        subtitle: 'Locations, capacity, and public visibility.',
        icon: Icons.warehouse_outlined,
        route: '/cargo/warehouses',
      ),
      FeatureMenuEntry(
        title: 'Sea bookings',
        subtitle: 'Review and manage sea freight bookings.',
        icon: Icons.directions_boat_outlined,
        route: '/cargo/sea-bookings',
      ),
      FeatureMenuEntry(
        title: 'Documentation workspace',
        subtitle: 'Packing lists, intake, and customer records.',
        icon: Icons.description_outlined,
        route: '/cargo/documentationworkspace',
      ),
      FeatureMenuEntry(
        title: 'Warehouse automation',
        subtitle: 'Scanning, matching, verification, and handover.',
        icon: Icons.qr_code_scanner_rounded,
        route: '/cargo/documentationworkspace/warehouse-automation',
      ),
      FeatureMenuEntry(
        title: 'Financial analytics',
        subtitle: 'Review financial performance and trends.',
        icon: Icons.analytics_outlined,
        route: '/cargo/finance',
      ),
      FeatureMenuEntry(
        title: 'Staff and branches',
        subtitle: 'Invite staff and assign branch permissions.',
        icon: Icons.groups_outlined,
        route: '/cargo/settings/staff-branches',
      ),
      FeatureMenuEntry(
        title: 'Billing and usage',
        subtitle: 'Plan limits, usage, and billing visibility.',
        icon: Icons.credit_card_outlined,
        route: '/cargo/settings/billing',
      ),
      FeatureMenuEntry(
        title: 'Shipment orders',
        subtitle: 'Manage customer shipment orders.',
        icon: Icons.local_shipping_outlined,
        route: '/cargo/shipment-orders',
      ),
      FeatureMenuEntry(
        title: 'FCL requests',
        subtitle: 'Review full-container quote requests.',
        icon: Icons.inventory_outlined,
        route: '/cargo/fcl-requests',
      ),
      FeatureMenuEntry(
        title: 'Express Air Cargo',
        subtitle: 'Manage air cargo bookings.',
        icon: Icons.flight_outlined,
        route: '/cargo/express-air-cargo',
      ),
      FeatureMenuEntry(
        title: 'Track shipments',
        subtitle: 'Search operational shipment timelines.',
        icon: Icons.route_outlined,
        route: '/cargo/track-shipments',
      ),
    ],
  );
}
