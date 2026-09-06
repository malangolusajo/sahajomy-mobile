import 'package:flutter/material.dart';

import '../../../core/ui/sahajomy_ui.dart';
import '../../../shared/presentation/feature_menu_page.dart';
import '../activity/presentation/super_admin_platform_activity_page.dart';
import '../dashboard/presentation/super_admin_dashboard_page.dart';
import '../users/presentation/super_admin_user_list_page.dart';

class SuperAdminShell extends StatefulWidget {
  const SuperAdminShell({super.key});
  @override
  State<SuperAdminShell> createState() => _SuperAdminShellState();
}

class _SuperAdminShellState extends State<SuperAdminShell> {
  var _index = 0;
  static const _titles = ['Home', 'Users', 'Activity', 'More'];
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: SahajomyWorkspaceHeader(
      role: 'Super Admin',
      title: _titles[_index],
    ),
    body: IndexedStack(
      index: _index,
      children: const [
        SuperAdminDashboardPage(),
        SuperAdminUserListPage(),
        SuperAdminPlatformActivityPage(),
        _SuperAdminMorePage(),
      ],
    ),
    bottomNavigationBar: SahajomyPreviewNavigation(
      selectedIndex: _index,
      onSelected: (value) => setState(() => _index = value),
      destinations: const [
        SahajomyNavigationDestination(label: 'Home', icon: Icons.home_outlined),
        SahajomyNavigationDestination(
          label: 'Users',
          icon: Icons.people_outline,
        ),
        SahajomyNavigationDestination(
          label: 'Activity',
          icon: Icons.history_outlined,
        ),
        SahajomyNavigationDestination(
          label: 'More',
          icon: Icons.more_horiz_rounded,
        ),
      ],
    ),
  );
}

class _SuperAdminMorePage extends StatelessWidget {
  const _SuperAdminMorePage();

  @override
  Widget build(BuildContext context) => const FeatureMenuPage(
    title: 'Platform governance',
    description:
        'Manage companies, approvals, commercial settings, and oversight.',
    showAccountActions: true,
    entries: [
      FeatureMenuEntry(
        title: 'Sourcing agents',
        subtitle: 'Review agent accounts and status.',
        icon: Icons.storefront_outlined,
        route: '/admin/sourcing-agents',
      ),
      FeatureMenuEntry(
        title: 'Cargo administrators',
        subtitle: 'Review operators and company access.',
        icon: Icons.admin_panel_settings_outlined,
        route: '/admin/operators',
      ),
      FeatureMenuEntry(
        title: 'Cargo companies',
        subtitle: 'Search and govern company records.',
        icon: Icons.business_outlined,
        route: '/admin/companies',
      ),
      FeatureMenuEntry(
        title: 'Bookings oversight',
        subtitle: 'Review bookings across the platform.',
        icon: Icons.event_note_outlined,
        route: '/admin/bookings',
      ),
      FeatureMenuEntry(
        title: 'Subscriptions and costs',
        subtitle: 'Plans, usage, and operating costs.',
        icon: Icons.payments_outlined,
        route: '/admin/subscriptions',
      ),
      FeatureMenuEntry(
        title: 'Pending approvals',
        subtitle: 'Process registration approvals.',
        icon: Icons.approval_outlined,
        route: '/admin/pending-approvals',
      ),
      FeatureMenuEntry(
        title: 'Goods classification',
        subtitle: 'Manage authoritative cargo categories.',
        icon: Icons.category_outlined,
        route: '/admin/goods',
      ),
      FeatureMenuEntry(
        title: 'Commission',
        subtitle: 'Review platform commission settings.',
        icon: Icons.percent_outlined,
        route: '/admin/commission',
      ),
      FeatureMenuEntry(
        title: 'Warehouse automation',
        subtitle: 'Control operator automation entitlements.',
        icon: Icons.qr_code_scanner_outlined,
        route: '/reference/super-admin-warehouse-automation',
      ),
      FeatureMenuEntry(
        title: 'Reservations',
        subtitle: 'Review platform reservation activity.',
        icon: Icons.event_available_outlined,
        route: '/admin/reservations',
      ),
      FeatureMenuEntry(
        title: 'Track shipments',
        subtitle: 'Search platform shipment timelines.',
        icon: Icons.route_outlined,
        route: '/admin/track-shipments',
      ),
      FeatureMenuEntry(
        title: 'Settings',
        subtitle: 'Review platform configuration.',
        icon: Icons.settings_outlined,
        route: '/reference/super-admin-settings',
      ),
    ],
  );
}
