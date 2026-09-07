import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../app/theme.dart';
import '../../../../core/ui/logistics_ui.dart';
import '../../../../core/ui/sahajomy_ui.dart';
import '../../../repository_providers.dart';
import '../domain/dashboard_summary.dart';
import '../../shipments/presentation/shipment_list_page.dart';
import '../../more/presentation/customer_more_page.dart';
import '../../orders/presentation/customer_order_list_page.dart';

class CustomerShell extends StatefulWidget {
  const CustomerShell({super.key});
  @override
  State<CustomerShell> createState() => _CustomerShellState();
}

class _CustomerShellState extends State<CustomerShell> {
  int _index = 0;
  final _visited = <int>{0};
  static const _pages = [
    CustomerHomePage(),
    ShipmentListPage(),
    CustomerOrderListPage(),
    CustomerMorePage(),
  ];
  static const _titles = [
    'My shipments & sourcing',
    'Shipments',
    'Sourcing orders',
    'My account',
  ];

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: Text(_titles[_index]),
          leading: const Padding(
            padding: EdgeInsets.all(12),
            child: SahajomyBrandMark(size: 32, showShadow: false),
          ),
          actions: [
            IconButton(
              tooltip: 'Shipment notifications',
              onPressed: () => context.push('/customer/notifications'),
              icon: const Icon(Icons.notifications_none_rounded),
            ),
          ],
        ),
        body: IndexedStack(
          index: _index,
          children: [
            for (var i = 0; i < _pages.length; i++)
              _visited.contains(i) ? _pages[i] : const SizedBox.shrink(),
          ],
        ),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _index,
          onDestinationSelected: (i) => setState(() {
            _index = i;
            _visited.add(i);
          }),
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.home_outlined),
              selectedIcon: Icon(Icons.home_rounded),
              label: 'Home',
            ),
            NavigationDestination(
              icon: Icon(Icons.local_shipping_outlined),
              label: 'Shipments',
            ),
            NavigationDestination(
              icon: Icon(Icons.storefront_outlined),
              label: 'Sourcing',
            ),
            NavigationDestination(
              icon: Icon(Icons.person_outline_rounded),
              label: 'Account',
            ),
          ],
        ),
      );
}

class CustomerHomePage extends ConsumerStatefulWidget {
  const CustomerHomePage({super.key});

  @override
  ConsumerState<CustomerHomePage> createState() => _CustomerHomeState();
}

class _CustomerHomeState extends ConsumerState<CustomerHomePage> {
  late Future<CustomerDashboardSummary> _summary;

  @override
  void initState() {
    super.initState();
    _summary = _load();
  }

  Future<CustomerDashboardSummary> _load() =>
      ref.read(customerDashboardRepositoryProvider).loadSummary();

  Future<void> _refresh() async {
    final next = _load();
    setState(() => _summary = next);
    try {
      await next;
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) => RefreshIndicator(
        onRefresh: _refresh,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(24, 20, 24, 32),
          children: [
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: brandNavyDark,
                borderRadius: BorderRadius.circular(22),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Hello there,',
                    style: TextStyle(
                      fontSize: 14,
                      color: Color(0xFFFFB89E),
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Welcome to\nSahajomy',
                    style: TextStyle(
                      fontSize: 28,
                      color: Colors.white,
                      fontWeight: FontWeight.w900,
                      height: 1.2,
                    ),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Let\'s get your cargo moving!',
                    style: TextStyle(color: Color(0xFFD1DEE6), fontSize: 14),
                  ),
                  const SizedBox(height: 20),
                  Row(
                    children: [
                      Expanded(
                        child: FilledButton(
                          style: FilledButton.styleFrom(
                            backgroundColor:
                                const Color(0xFFFFB89E),
                            foregroundColor: brandNavyDark,
                          ),
                          onPressed: () =>
                              context.push('/customer/booking-hub'),
                          child: const Text('Book shipment'),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 28),
            Text('Active shipments',
                style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 14),
            FutureBuilder<CustomerDashboardSummary>(
              future: _summary,
              builder: (context, snapshot) {
                if (snapshot.connectionState != ConnectionState.done) {
                  return const LinearProgressIndicator();
                }
                if (snapshot.hasError) {
                  return SahajomyMessageState(
                    icon: Icons.cloud_off_outlined,
                    message: logisticsError(
                        snapshot.error, 'shipping overview'),
                    actionLabel: 'Reload overview',
                    onAction: _refresh,
                  );
                }
                final value = snapshot.data!;
                return Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    _Count(
                        label: 'Shipments',
                        count: value.shipments,
                        route: '/customer/shipments'),
                    _Count(
                        label: 'Sea bookings',
                        count: value.bookings,
                        route: '/customer/sea-bookings'),
                    _Count(
                        label: 'Sourcing orders',
                        count: value.orders,
                        route: '/customer/orders'),
                  ],
                );
              },
            ),
            const SizedBox(height: 28),
            Text('Quick actions',
                style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 12),
            _Action(
              icon: Icons.local_shipping_outlined,
              title: 'Book shipment',
              description: 'Sea or air cargo booking',
              route: '/customer/booking-hub',
            ),
            _Action(
              icon: Icons.route_outlined,
              title: 'Track shipments',
              description: 'Warehouse and shipping milestones',
              route: '/customer/track-shipment',
            ),
            _Action(
              icon: Icons.location_on_outlined,
              title: 'China warehouse addresses',
              description:
                  'Copy your address and supplier shipping mark',
              route: '/customer/china-addresses',
            ),
            _Action(
              icon: Icons.description_outlined,
              title: 'Shipping documents',
              description: 'Invoices, receipts and packing lists',
              route: '/customer/documents',
            ),
            _Action(
              icon: Icons.receipt_long_outlined,
              title: 'My bookings',
              description: 'View all sea and air bookings',
              route: '/customer/my-bookings',
            ),
          ],
        ),
      );
}

class _Count extends StatelessWidget {
  const _Count(
      {required this.label, required this.count, required this.route});

  final String label;
  final int count;
  final String route;

  @override
  Widget build(BuildContext context) => SizedBox(
        width: 144,
        child: InkWell(
          onTap: () => context.push(route),
          borderRadius: BorderRadius.circular(14),
          child: Padding(
            padding: const EdgeInsets.symmetric(
                vertical: 14, horizontal: 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('$count',
                    style:
                        Theme.of(context).textTheme.headlineMedium),
                const SizedBox(height: 4),
                Text(label),
              ],
            ),
          ),
        ),
      );
}

class _Action extends StatelessWidget {
  const _Action({
    required this.icon,
    required this.title,
    required this.description,
    required this.route,
  });

  final IconData icon;
  final String title;
  final String description;
  final String route;

  @override
  Widget build(BuildContext context) => Column(
        children: [
          ListTile(
            contentPadding:
                const EdgeInsets.symmetric(vertical: 8),
            leading: Icon(icon, color: brandNavy),
            title: Text(title,
                style:
                    const TextStyle(fontWeight: FontWeight.w700)),
            subtitle: Text(description),
            trailing:
                const Icon(Icons.chevron_right_rounded),
            onTap: () => context.push(route),
          ),
          const Divider(height: 1),
        ],
      );
}
