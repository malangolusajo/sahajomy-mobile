import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../app/theme.dart';
import '../../../customer/presentation/customer_components.dart';
import '../../../repository_providers.dart';
import '../../batches/data/sourcing_agent_batches_repository.dart';
import '../../batches/presentation/sourcing_agent_batch_workflow_pages.dart';

class SourcingAgentProductManagementPage extends ConsumerStatefulWidget {
  const SourcingAgentProductManagementPage({super.key});

  @override
  ConsumerState<SourcingAgentProductManagementPage> createState() =>
      _SourcingAgentProductManagementPageState();
}

class _SourcingAgentProductManagementPageState
    extends ConsumerState<SourcingAgentProductManagementPage> {
  SourcingAgentBatchesRepository get _repository =>
      ref.read(sourcingAgentBatchesRepositoryProvider);
  late Future<List<Map<String, dynamic>>> _batches;
  String? _selectedBatchId;
  String? _selectedBatchTitle;
  Future<List<Map<String, dynamic>>>? _products;

  @override
  void initState() {
    super.initState();
    _batches = _loadBatches();
  }

  Future<List<Map<String, dynamic>>> _loadBatches() async {
    final res = await _repository.listBatches();
    final batches = (res['batches'] as List? ?? const [])
        .cast<Map<String, dynamic>>();
    if (batches.isNotEmpty) {
      _selectedBatchId = '${batches.first['id']}';
      _selectedBatchTitle = batches.first['title'] as String?;
      _products = _repository.listProducts(_selectedBatchId!);
    }
    return batches;
  }

  void _selectBatch(Map<String, dynamic> batch) {
    setState(() {
      _selectedBatchId = '${batch['id']}';
      _selectedBatchTitle = batch['title'] as String?;
      _products = _repository.listProducts(_selectedBatchId!);
    });
  }

  Future<void> _refresh() async {
    setState(() {
      _batches = _loadBatches();
    });
    await _batches;
    if (_selectedBatchId != null) {
      setState(() {
        _products = _repository.listProducts(_selectedBatchId!);
      });
    }
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'SOURCING AGENT',
    title: 'Product management',
    notificationRoute: '/reference/agent-notifications',
    body: RefreshIndicator(
      onRefresh: _refresh,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          const CustomerHeroCard(
            eyebrow: 'Agizisha products',
            title: 'Your product catalogue',
            subtitle: 'Add clear product photos so customers can identify and order with confidence.',
          ),
          const SizedBox(height: 16),
          FutureBuilder<List<Map<String, dynamic>>>(
            future: _batches,
            builder: (context, snapshot) {
              if (snapshot.connectionState != ConnectionState.done) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snapshot.hasError) {
                return CustomerEmptyState(
                  icon: Icons.wifi_off_rounded,
                  message: 'Could not load batches.',
                  actionLabel: 'Retry',
                  onAction: _refresh,
                );
              }
              final batches = snapshot.data ?? [];
              if (batches.isEmpty) {
                return const CustomerEmptyState(
                  icon: Icons.inventory_2_outlined,
                  message: 'No batches yet. Create a batch first to add products.',
                );
              }
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const CustomerSectionHeader(title: 'Select batch'),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: batches.map((b) {
                      final selected = '${b['id']}' == _selectedBatchId;
                      return ChoiceChip(
                        label: Text(b['title'] as String? ?? 'Batch'),
                        selected: selected,
                        onSelected: (_) => _selectBatch(b),
                        backgroundColor: Colors.white,
                        selectedColor: brandCoral.withValues(alpha: 0.15),
                        labelStyle: TextStyle(
                          color: selected ? brandCoral : appMuted,
                          fontWeight: FontWeight.w600,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(20),
                          side: BorderSide(
                            color: selected ? brandCoral : appBorder,
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 20),
                  if (_selectedBatchId != null)
                    FutureBuilder<List<Map<String, dynamic>>>(
                      future: _products,
                      builder: (context, ps) {
                        if (ps.connectionState != ConnectionState.done) {
                          return const _ProductGridSkeleton();
                        }
                        if (ps.hasError) {
                          return CustomerEmptyState(
                            icon: Icons.error_outline,
                            message: 'Could not load products.',
                            actionLabel: 'Retry',
                            onAction: () => setState(() {
                              _products =
                                  _repository.listProducts(_selectedBatchId!);
                            }),
                          );
                        }
                        final products = ps.data ?? [];
                        if (products.isEmpty) {
                          return CustomerEmptyState(
                            icon: Icons.image_outlined,
                            message: 'No products in this batch yet.',
                            actionLabel: 'Add product',
                            onAction: () => Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) => SourcingAgentAddProductPage(
                                  batchId: _selectedBatchId!,
                                  batchTitle: _selectedBatchTitle,
                                ),
                              ),
                            ),
                          );
                        }
                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            CustomerSectionHeader(
                              title: 'Products (${products.length})',
                            ),
                            const SizedBox(height: 12),
                            GridView.builder(
                              shrinkWrap: true,
                              physics: const NeverScrollableScrollPhysics(),
                              gridDelegate:
                                  const SliverGridDelegateWithFixedCrossAxisCount(
                                crossAxisCount: 2,
                                mainAxisSpacing: 14,
                                crossAxisSpacing: 14,
                                childAspectRatio: 0.72,
                              ),
                              itemCount: products.length,
                              itemBuilder: (context, i) =>
                                  _ProductCard(product: products[i]),
                            ),
                          ],
                        );
                      },
                    ),
                ],
              );
            },
          ),
        ],
      ),
    ),
    floatingActionButton: _selectedBatchId == null
        ? null
        : FloatingActionButton.extended(
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => SourcingAgentAddProductPage(
                  batchId: _selectedBatchId!,
                  batchTitle: _selectedBatchTitle,
                ),
              ),
            ),
            icon: const Icon(Icons.add_a_photo_outlined),
            label: const Text('Add product'),
            backgroundColor: brandCoral,
          ),
  );
}

class _ProductCard extends StatelessWidget {
  const _ProductCard({required this.product});
  final Map<String, dynamic> product;

  @override
  Widget build(BuildContext context) {
    final imageUrl = product['image_url'] as String?;
    final name = product['name'] as String? ?? 'Product';
    final price = product['price_per_unit'];
    final status = (product['status'] as String? ?? 'draft')
        .replaceAll('_', ' ');
    final goodsType = product['goods_type_name'] as String?;

    return InkWell(
      borderRadius: BorderRadius.circular(16),
      onTap: () {
        // TODO: navigate to edit product page
      },
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: appBorder),
        ),
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            AspectRatio(
              aspectRatio: 1,
              child: _ProductImage(url: imageUrl, name: name),
            ),
            Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    name,
                    style: const TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 14,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  if (goodsType != null) ...[
                    const SizedBox(height: 3),
                    Text(
                      goodsType,
                      style: const TextStyle(color: appMuted, fontSize: 12),
                    ),
                  ],
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          price != null ? '$price' : '—',
                          style: const TextStyle(
                            fontWeight: FontWeight.w800,
                            fontSize: 15,
                            color: brandCoral,
                          ),
                        ),
                      ),
                      CustomerStatusPill(label: status),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ProductImage extends StatelessWidget {
  const _ProductImage({this.url, required this.name});
  final String? url;
  final String name;

  @override
  Widget build(BuildContext context) {
    if (url == null || url!.isEmpty) {
      return Container(
        color: appCanvas,
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.image_outlined, size: 40, color: appMuted),
              const SizedBox(height: 6),
              Text(
                'No photo',
                style: TextStyle(color: appMuted.withValues(alpha: 0.7), fontSize: 11),
              ),
            ],
          ),
        ),
      );
    }
    return Image.network(
      url!,
      fit: BoxFit.cover,
      errorBuilder: (context, error, stackTrace) => Container(
        color: appCanvas,
        child: const Center(
          child: Icon(Icons.broken_image_outlined, size: 36, color: appMuted),
        ),
      ),
      loadingBuilder: (context, child, progress) {
        if (progress == null) return child;
        return Container(
          color: appCanvas,
          child: Center(
            child: CircularProgressIndicator(
              value: progress.expectedTotalBytes != null
                  ? progress.cumulativeBytesLoaded /
                      progress.expectedTotalBytes!
                  : null,
              color: brandCoral,
              strokeWidth: 2,
            ),
          ),
        );
      },
    );
  }
}

class _ProductGridSkeleton extends StatelessWidget {
  const _ProductGridSkeleton();

  @override
  Widget build(BuildContext context) => GridView.builder(
    shrinkWrap: true,
    physics: const NeverScrollableScrollPhysics(),
    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
      crossAxisCount: 2,
      mainAxisSpacing: 14,
      crossAxisSpacing: 14,
      childAspectRatio: 0.72,
    ),
    itemCount: 4,
    itemBuilder: (context, i) => Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: appBorder),
      ),
      child: Column(
        children: [
          Expanded(
            child: Container(
              color: appCanvas,
              child: const Center(
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(height: 14, width: 100, decoration: BoxDecoration(color: appBorder, borderRadius: BorderRadius.circular(4))),
                const SizedBox(height: 6),
                Container(height: 12, width: 60, decoration: BoxDecoration(color: appBorder, borderRadius: BorderRadius.circular(4))),
              ],
            ),
          ),
        ],
      ),
    ),
  );
}
