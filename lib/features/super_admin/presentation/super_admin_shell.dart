import 'package:flutter/material.dart';

import '../../../core/ui/sahajomy_ui.dart';
import '../activity/presentation/super_admin_platform_activity_page.dart';
import '../dashboard/presentation/super_admin_dashboard_page.dart';
import '../users/presentation/super_admin_user_list_page.dart';
import '../warehouse_automation/presentation/super_admin_warehouse_automation_page.dart';

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
        SuperAdminWarehouseAutomationPage(),
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
