import 'package:flutter/material.dart';

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
          onPressed: () {},
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

class _CustomerHome extends StatelessWidget {
  const _CustomerHome();

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
    children: [
      Text(
        'Good morning, customer',
        style: Theme.of(context).textTheme.headlineMedium,
      ),
      const SizedBox(height: 6),
      const Text(
        'Your cargo is moving. Here is a quick view of your shipments and reservations.',
      ),
      const SizedBox(height: 20),
      Card(
        child: ListTile(
          contentPadding: const EdgeInsets.all(16),
          title: const Text(
            '1 shipment in transit',
            style: TextStyle(fontWeight: FontWeight.w800),
          ),
          subtitle: const Padding(
            padding: EdgeInsets.only(top: 5),
            child: Text('Open the live operational overview.'),
          ),
          trailing: const Chip(label: Text('Live')),
          onTap: () => Navigator.pushNamed(context, '/customer/track-shipment'),
        ),
      ),
      const SizedBox(height: 12),
      Card(
        child: ListTile(
          contentPadding: const EdgeInsets.all(16),
          title: const Text(
            'Reserve container space',
            style: TextStyle(fontWeight: FontWeight.w800),
          ),
          subtitle: const Padding(
            padding: EdgeInsets.only(top: 5),
            child: Text('Handle today’s next action.'),
          ),
          trailing: const Chip(label: Text('Action')),
        ),
      ),
      const SizedBox(height: 20),
      FilledButton(onPressed: () {}, child: const Text('Reserve space')),
      const SizedBox(height: 28),
      Text('Quick actions', style: Theme.of(context).textTheme.titleLarge),
      const SizedBox(height: 12),
      Wrap(
        spacing: 12,
        runSpacing: 12,
        children: [
          const _ActionCard(
            icon: Icons.qr_code_scanner_rounded,
            label: 'Scan collection QR',
          ),
          const _ActionCard(
            icon: Icons.flight_takeoff_outlined,
            label: 'Express air cargo',
          ),
          _ActionCard(
            icon: Icons.location_on_outlined,
            label: 'China addresses',
            onTap: () =>
                Navigator.pushNamed(context, '/customer/china-addresses'),
          ),
          const _ActionCard(
            icon: Icons.description_outlined,
            label: 'Documents',
          ),
        ],
      ),
    ],
  );
}

class _ActionCard extends StatelessWidget {
  const _ActionCard({required this.icon, required this.label, this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: 164,
    child: Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, color: const Color(0xFFFF6B4A)),
              const SizedBox(height: 16),
              Text(label, style: const TextStyle(fontWeight: FontWeight.w700)),
            ],
          ),
        ),
      ),
    ),
  );
}
