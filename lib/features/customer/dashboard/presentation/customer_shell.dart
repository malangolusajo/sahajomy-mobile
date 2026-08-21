import 'package:flutter/material.dart';

import '../../../../core/ui/sahajomy_ui.dart';
import '../data/customer_dashboard_repository.dart';
import '../../shipments/presentation/shipment_list_page.dart';
import '../../more/presentation/customer_more_page.dart';
import '../../orders/presentation/customer_order_list_page.dart';

class CustomerShell extends StatefulWidget {
  const CustomerShell({super.key});

  @override
  State<CustomerShell> createState() => _CustomerShellState();
}

class _CustomerShellState extends State<CustomerShell> {
  var _selectedIndex = 0;
  static const _titles = ['Home', 'Shipments', 'Agizisha', 'More'];

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text(
            'CUSTOMER',
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.4,
              color: Color(0xFFFF6B4A),
            ),
          ),
          Text(
            _titles[_selectedIndex],
            style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800),
          ),
        ],
      ),
      centerTitle: true,
      actions: [
        IconButton(
          tooltip: 'Notifications',
          onPressed: () =>
              Navigator.pushNamed(context, '/customer/notifications'),
          icon: const Badge(child: Icon(Icons.notifications_none_rounded)),
        ),
      ],
    ),
    body: IndexedStack(
      index: _selectedIndex,
      children: [
        const _CustomerHome(),
        const ShipmentListPage(),
        const CustomerOrderListPage(),
        const CustomerMorePage(),
      ],
    ),
    bottomNavigationBar: NavigationBar(
      selectedIndex: _selectedIndex,
      onDestinationSelected: (index) => setState(() => _selectedIndex = index),
      destinations: const [
        NavigationDestination(
          icon: Icon(Icons.home_outlined),
          selectedIcon: Icon(Icons.home),
          label: 'Home',
        ),
        NavigationDestination(
          icon: Icon(Icons.local_shipping_outlined),
          selectedIcon: Icon(Icons.local_shipping),
          label: 'Shipments',
        ),
        NavigationDestination(
          icon: Icon(Icons.storefront_outlined),
          selectedIcon: Icon(Icons.storefront),
          label: 'Agizisha',
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

class _CustomerHome extends StatefulWidget {
  const _CustomerHome();

  @override
  State<_CustomerHome> createState() => _CustomerHomeState();
}

class _CustomerHomeState extends State<_CustomerHome> {
  final _repository = CustomerDashboardRepository();
  late Future<CustomerDashboardSummary> _summary = _repository.loadSummary();

  void _retry() => setState(() => _summary = _repository.loadSummary());

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
    children: [
      Text(
        'Good morning, Amina',
        style: Theme.of(context).textTheme.headlineMedium,
      ),
      const SizedBox(height: 6),
      const Text(
        'Your cargo is moving. Here is a quick view of your shipments and reservations.',
      ),
      const SizedBox(height: 20),
      FutureBuilder<CustomerDashboardSummary>(
        future: _summary,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const _DashboardRow(
              title: 'Loading your cargo overview...',
              description: 'Fetching the latest shipment details.',
              status: 'Loading',
            );
          }
          if (snapshot.hasError) {
            return _DashboardRow(
              title: 'Your overview is unavailable.',
              description: 'Check your connection, then try again.',
              status: 'Retry',
              onTap: _retry,
            );
          }
          final summary = snapshot.data!;
          return _DashboardRow(
            title:
                '${summary.shipments} shipment${summary.shipments == 1 ? '' : 's'} in transit',
            description: 'Open the live operational overview.',
            status: 'Live',
            onTap: () =>
                Navigator.pushNamed(context, '/customer/track-shipment'),
          );
        },
      ),
      const SizedBox(height: 12),
      _DashboardRow(
        title: 'Reserve container space',
        description: 'Handle today\'s next action.',
        status: 'Action',
        onTap: () => Navigator.pushNamed(context, '/customer/containers'),
      ),
      const SizedBox(height: 20),
      FilledButton(
        onPressed: () => Navigator.pushNamed(context, '/customer/containers'),
        child: const Text('Reserve space'),
      ),
    ],
  );
}

class _DashboardRow extends StatelessWidget {
  const _DashboardRow({
    required this.title,
    required this.description,
    required this.status,
    this.onTap,
  });

  final String title;
  final String description;
  final String status;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Card(
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    description,
                    style: const TextStyle(fontSize: 12, height: 1.5),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            SahajomyStatusPill(label: status),
          ],
        ),
      ),
    ),
  );
}
