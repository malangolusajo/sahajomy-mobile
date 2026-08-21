import 'package:flutter/material.dart';

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
    appBar: AppBar(title: Text(_titles[_index])),
    body: IndexedStack(
      index: _index,
      children: const [
        SuperAdminDashboardPage(),
        SuperAdminUserListPage(),
        _PendingPage('Activity'),
        _PendingPage('More'),
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
          icon: Icon(Icons.people_outline),
          selectedIcon: Icon(Icons.people),
          label: 'Users',
        ),
        NavigationDestination(
          icon: Icon(Icons.history_outlined),
          selectedIcon: Icon(Icons.history),
          label: 'Activity',
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

class _PendingPage extends StatelessWidget {
  const _PendingPage(this.title);
  final String title;
  @override
  Widget build(BuildContext context) =>
      Center(child: Text('$title is the next Super Admin checkpoint.'));
}
