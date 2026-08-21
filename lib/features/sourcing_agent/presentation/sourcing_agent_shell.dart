import 'package:flutter/material.dart';

import '../batches/presentation/sourcing_agent_batch_list_page.dart';

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
    appBar: AppBar(title: Text(_titles[_index])),
    body: IndexedStack(
      index: _index,
      children: const [
        _AgentPendingPage(title: 'Sourcing Agent home'),
        SourcingAgentBatchListPage(),
        _AgentPendingPage(title: 'Orders'),
        _AgentPendingPage(title: 'More'),
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
          icon: Icon(Icons.inventory_2_outlined),
          selectedIcon: Icon(Icons.inventory_2),
          label: 'Batches',
        ),
        NavigationDestination(
          icon: Icon(Icons.shopping_bag_outlined),
          selectedIcon: Icon(Icons.shopping_bag),
          label: 'Orders',
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

class _AgentPendingPage extends StatelessWidget {
  const _AgentPendingPage({required this.title});
  final String title;
  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(32),
      child: Text(
        '$title is the next Sourcing Agent checkpoint.',
        textAlign: TextAlign.center,
      ),
    ),
  );
}
