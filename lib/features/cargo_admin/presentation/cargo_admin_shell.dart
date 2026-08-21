import 'package:flutter/material.dart';

import '../dashboard/presentation/cargo_admin_dashboard_page.dart';
import '../containers/presentation/cargo_admin_container_list_page.dart';

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
    appBar: AppBar(title: Text(_titles[_index])),
    body: IndexedStack(
      index: _index,
      children: const [
        CargoAdminDashboardPage(),
        CargoAdminContainerListPage(),
        _CargoAdminPendingPage(title: 'Documents'),
        _CargoAdminPendingPage(title: 'More'),
      ],
    ),
    bottomNavigationBar: NavigationBar(
      selectedIndex: _index,
      onDestinationSelected: (value) => setState(() => _index = value),
      destinations: const [
        NavigationDestination(
          icon: Icon(Icons.home_outlined),
          selectedIcon: Icon(Icons.home),
          label: 'Home',
        ),
        NavigationDestination(
          icon: Icon(Icons.settings_outlined),
          selectedIcon: Icon(Icons.settings),
          label: 'Operations',
        ),
        NavigationDestination(
          icon: Icon(Icons.description_outlined),
          selectedIcon: Icon(Icons.description),
          label: 'Documents',
        ),
        NavigationDestination(
          icon: Icon(Icons.grid_view_outlined),
          selectedIcon: Icon(Icons.grid_view),
          label: 'More',
        ),
      ],
    ),
  );
}

class _CargoAdminPendingPage extends StatelessWidget {
  const _CargoAdminPendingPage({required this.title});
  final String title;

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(32),
      child: Text(
        '$title tools are the next Cargo Admin checkpoint.',
        textAlign: TextAlign.center,
      ),
    ),
  );
}
