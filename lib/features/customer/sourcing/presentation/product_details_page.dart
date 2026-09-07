import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../app/theme.dart';
import '../../../../features/repository_providers.dart';
import '../../presentation/customer_components.dart';
import 'request_product_page.dart';

class ProductDetailsPage extends ConsumerStatefulWidget {
  const ProductDetailsPage({required this.productId, super.key});

  final String productId;

  @override
  ConsumerState<ProductDetailsPage> createState() => _ProductDetailsPageState();
}

class _ProductDetailsPageState extends ConsumerState<ProductDetailsPage> {
  late Future<Map<String, dynamic>> _product;

  @override
  void initState() {
    super.initState();
    _product = ref.read(publicServicesRepositoryProvider).getProduct(widget.productId);
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Product details',
    body: FutureBuilder<Map<String, dynamic>>(
      future: _product,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return CustomerEmptyState(
            icon: Icons.error_outline,
            message: 'Could not load this product.',
            actionLabel: 'Retry',
            onAction: () => setState(() {
              _product = ref.read(publicServicesRepositoryProvider).getProduct(widget.productId);
            }),
          );
        }
        final p = snapshot.data!;
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          children: [
            CustomerHeroCard(
              eyebrow: 'Product',
              title: p['name'] ?? 'Product',
              subtitle: p['description'] ?? '',
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: appBorder),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Unit price', style: TextStyle(color: appMuted, fontSize: 12)),
                        const SizedBox(height: 4),
                        Text(
                          '${p['currency'] ?? ''} ${p['price_per_unit'] ?? '—'}',
                          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: appBorder),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Min. order', style: TextStyle(color: appMuted, fontSize: 12)),
                        const SizedBox(height: 4),
                        Text(
                          '${p['min_order_quantity'] ?? '1'} pcs',
                          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: appBorder),
              ),
              child: Column(
                children: [
                  _detailRow('CO', 'Colors', (p['attributes'] as Map?)?['colors'] ?? '—', brandCoral),
                  const Divider(height: 1, indent: 60),
                  _detailRow('SZ', 'Size', (p['attributes'] as Map?)?['size'] ?? '—', appMuted),
                  const Divider(height: 1, indent: 60),
                  _detailRow('AG', 'Agent', p['agent_name'] ?? 'Sourcing agent', appMuted),
                ],
              ),
            ),
            const SizedBox(height: 20),
            FilledButton(
              onPressed: () {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => RequestProductPage(product: p),
                  ),
                );
              },
              child: const Text('Request this product'),
            ),
          ],
        );
      },
    ),
  );

  Widget _detailRow(String badge, String title, String subtitle, Color badgeColor) => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    child: Row(
      children: [
        Container(
          width: 40,
          height: 40,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: badgeColor.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Text(badge, style: TextStyle(color: badgeColor, fontWeight: FontWeight.w800)),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
              const SizedBox(height: 2),
              Text(subtitle, style: const TextStyle(color: appMuted, fontSize: 13)),
            ],
          ),
        ),
      ],
    ),
  );
}
