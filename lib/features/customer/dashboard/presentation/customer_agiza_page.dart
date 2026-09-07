import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../../../core/ui/logistics_ui.dart';
import '../../../../core/ui/sahajomy_ui.dart';
import '../../../repository_providers.dart';
import '../../presentation/customer_components.dart';

class CustomerAgizaPage extends ConsumerStatefulWidget {
  const CustomerAgizaPage({super.key});

  @override
  ConsumerState<CustomerAgizaPage> createState() => _CustomerAgizaPageState();
}

class _CustomerAgizaPageState extends ConsumerState<CustomerAgizaPage> {
  late Future<List<Map<String, dynamic>>> _orders;

  @override
  void initState() {
    super.initState();
    _orders = _load();
  }

  Future<List<Map<String, dynamic>>> _load() =>
      ref.read(customerOrdersRepositoryProvider).listOrders();

  Future<void> _refresh() async {
    final next = _load();
    setState(() => _orders = next);
    try {
      await next;
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Agiza',
    showBack: false,
    body: RefreshIndicator(
      onRefresh: _refresh,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
        children: [
          const CustomerHeroCard(
            eyebrow: 'Agiza',
            title: 'Find products from China',
            subtitle: 'Browse products posted by registered sourcing agents or request sourcing help.',
          ),
          const SizedBox(height: 28),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              CustomerQuickAction(
                label: 'Search',
                icon: const Icon(Icons.search, color: Colors.white, size: 24),
                onTap: () => context.push('/agizisha'),
              ),
              CustomerQuickAction(
                label: 'Agents',
                color: brandNavy,
                icon: const Text('AG', style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w800)),
                onTap: () => context.push('/agizisha'),
              ),
              CustomerQuickAction(
                label: 'Products',
                color: brandNavy,
                icon: const Text('PR', style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w800)),
                onTap: () => context.push('/agizisha'),
              ),
              CustomerQuickAction(
                label: 'Requests',
                color: brandNavy,
                icon: const Text('RQ', style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w800)),
                onTap: () => context.push('/customer/orders'),
              ),
            ],
          ),
          const SizedBox(height: 28),
          const CustomerSectionHeader(title: 'Sourcing orders'),
          const SizedBox(height: 14),
          FutureBuilder<List<Map<String, dynamic>>>(
            future: _orders,
            builder: (context, snapshot) {
              if (snapshot.connectionState != ConnectionState.done) {
                return const CustomerSkeletonList();
              }
              if (snapshot.hasError) {
                return SahajomyMessageState(
                  icon: Icons.cloud_off_outlined,
                  message: logisticsError(snapshot.error, 'sourcing orders'),
                  actionLabel: 'Reload',
                  onAction: _refresh,
                );
              }
              final items = snapshot.data ?? [];
              if (items.isEmpty) {
                return const CustomerEmptyState(
                  icon: Icons.shopping_bag_outlined,
                  message: 'No sourcing orders yet. Browse Agiza products or request sourcing help.',
                  actionLabel: 'Browse products',
                );
              }
              return Column(
                children: [
                  for (final item in items)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: _OrderRow(item: item),
                    ),
                ],
              );
            },
          ),
        ],
      ),
    ),
  );
}

class _OrderRow extends StatelessWidget {
  const _OrderRow({required this.item});

  final Map<String, dynamic> item;

  @override
  Widget build(BuildContext context) {
    final ref = item['order_number'] ?? item['name'] ?? 'Order';
    final status = item['status'] ?? 'Processing';
    final desc = item['order_description'] ?? item['description'] ?? 'Sourcing request';
    final id = item['id']?.toString() ?? '$ref';

    return CustomerListItem(
      badgeLabel: 'P${(item.hashCode % 90 + 10)}',
      badgeColor: brandCoral,
      title: '$ref',
      subtitle: '$desc',
      status: status.toString().replaceAll('_', ' '),
      onTap: () => context.push('/customer/orders/$id'),
    );
  }
}
