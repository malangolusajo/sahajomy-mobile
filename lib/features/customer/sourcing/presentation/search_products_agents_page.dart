import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../app/theme.dart';
import '../../../../features/repository_providers.dart';
import '../../presentation/customer_components.dart';
import 'sourcing_agent_page.dart';

class SearchProductsAgentsPage extends ConsumerStatefulWidget {
  const SearchProductsAgentsPage({super.key});

  @override
  ConsumerState<SearchProductsAgentsPage> createState() => _SearchProductsAgentsPageState();
}

class _SearchProductsAgentsPageState extends ConsumerState<SearchProductsAgentsPage> {
  int _tab = 0;
  String _query = '';
  late Future<List<Map<String, dynamic>>> _products;
  late Future<List<Map<String, dynamic>>> _agents;

  @override
  void initState() {
    super.initState();
    _products = ref.read(publicServicesRepositoryProvider).listMarketplaceProducts();
    _agents = ref.read(publicServicesRepositoryProvider).listMarketplaceAgents();
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Search products & agents',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        TextField(
          onChanged: (v) => setState(() => _query = v.toLowerCase()),
          decoration: const InputDecoration(
            prefixIcon: Icon(Icons.search_rounded),
            hintText: 'Product, supplier, or sourcing agent',
          ),
        ),
        const SizedBox(height: 16),
        SegmentedButton<int>(
          segments: const [
            ButtonSegment(value: 0, label: Text('Products')),
            ButtonSegment(value: 1, label: Text('Agents')),
          ],
          selected: {_tab},
          onSelectionChanged: (s) => setState(() => _tab = s.first),
        ),
        const SizedBox(height: 20),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text('Results', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
            FutureBuilder<List<Map<String, dynamic>>>(
              future: _tab == 0 ? _products : _agents,
              builder: (context, snapshot) => Text(
                '${snapshot.data?.where((e) => _matches(e)).length ?? 0} found',
                style: const TextStyle(color: appMuted, fontSize: 13),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        FutureBuilder<List<Map<String, dynamic>>>(
          future: _tab == 0 ? _products : _agents,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snapshot.hasError) {
              return CustomerEmptyState(
                icon: Icons.search_off,
                message: 'Could not load results.',
                actionLabel: 'Retry',
                onAction: () => setState(() {
                  _products = ref.read(publicServicesRepositoryProvider).listMarketplaceProducts();
                  _agents = ref.read(publicServicesRepositoryProvider).listMarketplaceAgents();
                }),
              );
            }
            final items = snapshot.data!.where(_matches).toList();
            if (items.isEmpty) {
              return const CustomerEmptyState(
                icon: Icons.search_off,
                message: 'No results match your search.',
              );
            }
            return Column(
              children: [
                for (final item in items)
                  _ResultRow(
                    title: _tab == 0
                        ? item['name'] ?? 'Product'
                        : item['name'] ?? item['company_name'] ?? 'Agent',
                    subtitle: _tab == 0
                        ? '${item['price_per_unit'] ?? ''} ${item['currency'] ?? ''}'
                        : '${item['products_count'] ?? 0} products · ${item['open_batches'] ?? 0} batches',
                    onTap: () {
                      if (_tab == 1) {
                        Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => SourcingAgentPage(agent: item),
                          ),
                        );
                      }
                    },
                  ),
              ],
            );
          },
        ),
      ],
    ),
  );

  bool _matches(Map<String, dynamic> item) {
    if (_query.isEmpty) return true;
    final name = (item['name'] ?? '').toString().toLowerCase();
    return name.contains(_query);
  }
}

class _ResultRow extends StatelessWidget {
  const _ResultRow({required this.title, required this.subtitle, this.onTap});

  final String title;
  final String subtitle;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Container(
    margin: const EdgeInsets.only(bottom: 8),
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(12),
      border: Border.all(color: appBorder),
    ),
    child: ListTile(
      leading: Container(
        width: 40,
        height: 40,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: brandCoral.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(10),
        ),
        child: const Text('P', style: TextStyle(color: brandCoral, fontWeight: FontWeight.w800)),
      ),
      title: Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
      subtitle: Text(subtitle, style: const TextStyle(color: appMuted, fontSize: 13)),
      trailing: const Icon(Icons.chevron_right, color: appMuted),
      onTap: onTap,
    ),
  );
}
