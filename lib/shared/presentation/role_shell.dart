import 'package:flutter/material.dart';

class RoleShell extends StatefulWidget {
  const RoleShell({super.key, required this.role, required this.destinations});
  final String role;
  final List<String> destinations;

  @override
  State<RoleShell> createState() => _RoleShellState();
}

class _RoleShellState extends State<RoleShell> {
  var _index = 0;

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text(widget.destinations[_index]),
      actions: [
        IconButton(
          onPressed: () {},
          icon: const Badge(child: Icon(Icons.notifications_none_rounded)),
        ),
      ],
    ),
    body: Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(widget.role, style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 8),
          Text(
            'This protected workspace is prepared for ${widget.destinations[_index].toLowerCase()} data from the deployed FastAPI service.',
          ),
          const SizedBox(height: 24),
          const Divider(),
          const SizedBox(height: 16),
          const Text(
            'Server access and actions are enabled after authenticated role routing.',
          ),
        ],
      ),
    ),
    bottomNavigationBar: NavigationBar(
      selectedIndex: _index,
      onDestinationSelected: (value) => setState(() => _index = value),
      destinations: widget.destinations
          .map(
            (label) => NavigationDestination(
              icon: const Icon(Icons.circle_outlined),
              selectedIcon: const Icon(Icons.circle),
              label: label,
            ),
          )
          .toList(),
    ),
  );
}
