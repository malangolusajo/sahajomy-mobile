import 'package:flutter/material.dart';

import '../../../core/ui/sahajomy_ui.dart';
import '../dashboard/presentation/cargo_admin_dashboard_page.dart';
import '../containers/presentation/cargo_admin_container_list_page.dart';
import '../documents/presentation/cargo_admin_documentation_workspace_page.dart';
import '../warehouse_automation/presentation/cargo_admin_warehouse_automation_page.dart';

class CargoAdminShell extends StatefulWidget {
  const CargoAdminShell({super.key});

  @override
  State<CargoAdminShell> createState() => _CargoAdminShellState();
}

class _CargoAdminShellState extends State<CargoAdminShell> {
  var _index = 0;
  static const _titles = ['Home', 'Operations', 'Documents', 'More'];

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: SahajomyWorkspaceHeader(
      role: 'Cargo Admin',
      title: _titles[_index],
    ),
    body: IndexedStack(
      index: _index,
      children: const [
        CargoAdminDashboardPage(),
        CargoAdminContainerListPage(),
        CargoAdminDocumentationWorkspacePage(),
        CargoAdminWarehouseAutomationPage(),
      ],
    ),
    bottomNavigationBar: SahajomyPreviewNavigation(
      selectedIndex: _index,
      onSelected: (value) => setState(() => _index = value),
      destinations: const [
        SahajomyNavigationDestination(label: 'Home', icon: Icons.home_outlined),
        SahajomyNavigationDestination(
          label: 'Operations',
          icon: Icons.settings_outlined,
        ),
        SahajomyNavigationDestination(
          label: 'Documents',
          icon: Icons.description_outlined,
        ),
        SahajomyNavigationDestination(
          label: 'More',
          icon: Icons.more_horiz_rounded,
        ),
      ],
    ),
  );
}
