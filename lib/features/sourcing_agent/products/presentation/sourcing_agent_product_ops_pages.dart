import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../app/theme.dart';
import '../../../customer/presentation/customer_components.dart';
import '../../../repository_providers.dart';

/// Screen 176 — Edit product
class AgentEditProductPage extends ConsumerStatefulWidget {
  const AgentEditProductPage({
    required this.batchId,
    required this.product,
    super.key,
  });
  final String batchId;
  final Map<String, dynamic> product;

  @override
  ConsumerState<AgentEditProductPage> createState() => _AgentEditProductPageState();
}

class _AgentEditProductPageState extends ConsumerState<AgentEditProductPage> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _name;
  late final TextEditingController _desc;
  late final TextEditingController _price;
  late final TextEditingController _moq;
  late final TextEditingController _imageUrl;
  String _status = 'draft';
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _name = TextEditingController(text: widget.product['name'] ?? '');
    _desc = TextEditingController(text: widget.product['description'] ?? '');
    _price = TextEditingController(text: '${widget.product['price_per_unit'] ?? ''}');
    _moq = TextEditingController(text: '${widget.product['minimum_order_quantity'] ?? ''}');
    _imageUrl = TextEditingController(text: widget.product['image_url'] ?? '');
    _status = widget.product['status'] ?? 'draft';
    _imageUrl.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _name.dispose(); _desc.dispose(); _price.dispose();
    _moq.dispose(); _imageUrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      await ref.read(sourcingAgentBatchesRepositoryProvider).updateProduct(
        batchId: widget.batchId,
        productId: '${widget.product['id']}',
        name: _name.text.trim(),
        description: _desc.text.trim(),
        pricePerUnit: double.tryParse(_price.text),
        minimumOrderQuantity: int.tryParse(_moq.text),
        imageUrl: _imageUrl.text.trim(),
        status: _status,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Product updated')));
        Navigator.of(context).pop(true);
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'SOURCING AGENT',
    title: 'Edit product',
    notificationRoute: '/reference/agent-notifications',
    body: Form(
      key: _formKey,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          CustomerHeroCard(
            eyebrow: 'Product',
            title: _name.text.isEmpty ? 'Edit details' : _name.text,
            subtitle: 'Update product info, photo and status.',
          ),
          const SizedBox(height: 16),
          Center(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: _imageUrl.text.isEmpty || Uri.tryParse(_imageUrl.text)?.hasAbsolutePath != true
                  ? Container(
                      width: 200, height: 200, color: appCanvas,
                      child: const Icon(Icons.image_outlined, size: 60, color: appMuted),
                    )
                  : Image.network(
                      _imageUrl.text, width: 200, height: 200, fit: BoxFit.cover,
                      errorBuilder: (_, _, _) => Container(
                        width: 200, height: 200, color: appCanvas,
                        child: const Icon(Icons.broken_image_outlined, size: 50, color: appMuted),
                      ),
                    ),
            ),
          ),
          const SizedBox(height: 16),
          TextFormField(controller: _name, decoration: const InputDecoration(labelText: 'Product name'), validator: (v) => v!.isEmpty ? 'Required' : null),
          const SizedBox(height: 14),
          TextFormField(controller: _desc, decoration: const InputDecoration(labelText: 'Description'), maxLines: 3),
          const SizedBox(height: 14),
          Row(children: [
            Expanded(child: TextFormField(controller: _price, decoration: const InputDecoration(labelText: 'Price / unit'), keyboardType: TextInputType.number)),
            const SizedBox(width: 12),
            Expanded(child: TextFormField(controller: _moq, decoration: const InputDecoration(labelText: 'MOQ'), keyboardType: TextInputType.number)),
          ]),
          const SizedBox(height: 14),
          TextFormField(controller: _imageUrl, decoration: const InputDecoration(labelText: 'Product image URL'), keyboardType: TextInputType.url),
          const SizedBox(height: 14),
          DropdownButtonFormField<String>(
            initialValue: _status,
            decoration: const InputDecoration(labelText: 'Status'),
            items: const ['draft', 'published', 'archived'].map((s) => DropdownMenuItem(value: s, child: Text(s))).toList(),
            onChanged: (v) => setState(() => _status = v ?? 'draft'),
          ),
          const SizedBox(height: 24),
          FilledButton.icon(onPressed: _busy ? null : _save, icon: const Icon(Icons.save), label: Text(_busy ? 'Saving...' : 'Save changes')),
        ],
      ),
    ),
  );
}

/// Screen 097 — Dynamic product attributes
class AgentDynamicAttributesPage extends ConsumerStatefulWidget {
  const AgentDynamicAttributesPage({required this.goodsTypeId, required this.goodsTypeName, super.key});
  final String goodsTypeId;
  final String goodsTypeName;

  @override
  ConsumerState<AgentDynamicAttributesPage> createState() => _AgentDynamicAttributesPageState();
}

class _AgentDynamicAttributesPageState extends ConsumerState<AgentDynamicAttributesPage> {
  late Future<Map<String, dynamic>> _future;
  final Map<String, dynamic> _values = {};

  @override
  void initState() {
    super.initState();
    _future = ref.read(sourcingAgentBatchesRepositoryProvider).getAttributeTemplates(widget.goodsTypeId);
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'PRODUCT ATTRIBUTES',
    title: 'Dynamic attributes',
    notificationRoute: '/reference/agent-notifications',
    body: FutureBuilder<Map<String, dynamic>>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return const CustomerEmptyState(icon: Icons.error_outline, message: 'Could not load attributes.');
        }
        final templates = (snapshot.data?['attributes'] as List? ?? []).cast<Map<String, dynamic>>();
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          children: [
            CustomerHeroCard(eyebrow: widget.goodsTypeName, title: 'Product attributes', subtitle: 'These attributes are specific to this goods type.'),
            const SizedBox(height: 16),
            if (templates.isEmpty)
              const CustomerEmptyState(icon: Icons.list_alt, message: 'No attribute templates for this goods type.')
            else
              for (final t in templates) ...[
                const SizedBox(height: 12),
                _attrField(t),
              ],
            if (templates.isNotEmpty) ...[
              const SizedBox(height: 24),
              FilledButton(onPressed: () => Navigator.pop(context, _values), child: const Text('Save attributes')),
            ],
          ],
        );
      },
    ),
  );

  Widget _attrField(Map<String, dynamic> t) {
    final name = t['name'] ?? 'Attribute';
    final type = t['type'] ?? 'text';
    final key = '${t['id'] ?? name}';
    if (type == 'select' || type == 'enum') {
      final options = (t['options'] as List? ?? []).cast<String>();
      return DropdownButtonFormField<String>(
        decoration: InputDecoration(labelText: name),
        items: options.map((o) => DropdownMenuItem(value: o, child: Text(o))).toList(),
        onChanged: (v) => setState(() => _values[key] = v),
      );
    }
    if (type == 'number') {
      return TextFormField(
        decoration: InputDecoration(labelText: name),
        keyboardType: TextInputType.number,
        onChanged: (v) => _values[key] = v,
      );
    }
    return TextFormField(
      decoration: InputDecoration(labelText: name),
      onChanged: (v) => _values[key] = v,
    );
  }
}

/// Screen 098 — Product variants
class AgentProductVariantsPage extends ConsumerStatefulWidget {
  const AgentProductVariantsPage({required this.product, super.key});
  final Map<String, dynamic> product;

  @override
  ConsumerState<AgentProductVariantsPage> createState() => _AgentProductVariantsPageState();
}

class _AgentProductVariantsPageState extends ConsumerState<AgentProductVariantsPage> {
  late List<Map<String, dynamic>> _variants;

  @override
  void initState() {
    super.initState();
    _variants = (widget.product['variants'] as List? ?? []).cast<Map<String, dynamic>>();
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'PRODUCT VARIANTS',
    title: 'Variants',
    notificationRoute: '/reference/agent-notifications',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        CustomerHeroCard(
          eyebrow: widget.product['name'] ?? 'Product',
          title: '${_variants.length} variant(s)',
          subtitle: 'Pricing and stock for each option combination.',
        ),
        const SizedBox(height: 16),
        if (_variants.isEmpty)
          const CustomerEmptyState(icon: Icons.layers_outlined, message: 'No variants defined for this product.')
        else
          for (var i = 0; i < _variants.length; i++) ...[
            if (i > 0) const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: appBorder)),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(_variants[i]['option_values']?.toString() ?? 'Variant ${i + 1}', style: const TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(child: _variantStat('Price', '${_variants[i]['price_per_unit'] ?? '—'}')),
                      Expanded(child: _variantStat('Stock', '${_variants[i]['stock_quantity'] ?? '—'}')),
                      Expanded(child: _variantStat('Active', (_variants[i]['is_active'] ?? false) ? 'Yes' : 'No')),
                    ],
                  ),
                ],
              ),
            ),
          ],
      ],
    ),
  );

  Widget _variantStat(String label, String value) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(label, style: const TextStyle(color: appMuted, fontSize: 11)),
      Text(value, style: const TextStyle(fontWeight: FontWeight.w700)),
    ],
  );
}

/// Screen 099 — Publish to Agiza
class AgentPublishPage extends ConsumerStatefulWidget {
  const AgentPublishPage({required this.batchId, super.key});
  final String batchId;

  @override
  ConsumerState<AgentPublishPage> createState() => _AgentPublishPageState();
}

class _AgentPublishPageState extends ConsumerState<AgentPublishPage> {
  late Future<List<Map<String, dynamic>>> _products;
  final Set<int> _selected = {};

  @override
  void initState() {
    super.initState();
    _products = ref.read(sourcingAgentBatchesRepositoryProvider).listProducts(widget.batchId);
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'PUBLISH',
    title: 'Publish to Agiza',
    notificationRoute: '/reference/agent-notifications',
    body: FutureBuilder<List<Map<String, dynamic>>>(
      future: _products,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final products = snapshot.data ?? [];
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          children: [
            const CustomerHeroCard(
              eyebrow: 'Agiza marketplace',
              title: 'Select products to publish',
              subtitle: 'Choose which products go live on the Agiza marketplace for customers.',
            ),
            const SizedBox(height: 16),
            if (products.isEmpty)
              const CustomerEmptyState(icon: Icons.shop_two_outlined, message: 'No products to publish.')
            else
              ...products.asMap().entries.map((e) {
                final idx = e.key;
                final p = e.value;
                return Container(
                  margin: const EdgeInsets.only(bottom: 12),
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: appBorder)),
                  child: CheckboxListTile(
                    value: _selected.contains(idx),
                    onChanged: (v) => setState(() => v == true ? _selected.add(idx) : _selected.remove(idx)),
                    title: Text(p['name'] ?? 'Product', style: const TextStyle(fontWeight: FontWeight.w700)),
                    subtitle: Text('${p['price_per_unit'] ?? '—'} • ${p['goods_type_name'] ?? ''}'),
                    secondary: ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: p['image_url'] != null
                          ? Image.network(p['image_url'], width: 48, height: 48, fit: BoxFit.cover,
                              errorBuilder: (_, _, _) => Container(width: 48, height: 48, color: appCanvas, child: const Icon(Icons.image_outlined, size: 24, color: appMuted)))
                          : Container(width: 48, height: 48, color: appCanvas, child: const Icon(Icons.image_outlined, size: 24, color: appMuted)),
                    ),
                  ),
                );
              }),
            if (products.isNotEmpty) ...[
              const SizedBox(height: 8),
              FilledButton.icon(
                onPressed: _selected.isEmpty ? null : () {
                  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Published ${_selected.length} product(s) to Agiza')));
                  Navigator.pop(context);
                },
                icon: const Icon(Icons.publish_rounded),
                label: Text('Publish ${_selected.isEmpty ? '' : '${_selected.length}'} selected'),
              ),
            ],
          ],
        );
      },
    ),
  );
}

/// Screen 100 — Share batch
class AgentShareBatchPage extends ConsumerStatefulWidget {
  const AgentShareBatchPage({required this.batchId, required this.batchTitle, super.key});
  final String batchId;
  final String batchTitle;

  @override
  ConsumerState<AgentShareBatchPage> createState() => _AgentShareBatchPageState();
}

class _AgentShareBatchPageState extends ConsumerState<AgentShareBatchPage> {
  final _expiresController = TextEditingController(text: '30');
  final _maxViewsController = TextEditingController();
  String? _shareUrl;
  bool _busy = false;

  @override
  void dispose() {
    _expiresController.dispose();
    _maxViewsController.dispose();
    super.dispose();
  }

  Future<void> _generate() async {
    setState(() => _busy = true);
    try {
      final res = await ref.read(sourcingAgentBatchesRepositoryProvider).shareBatch(
        batchId: widget.batchId,
        expiresDays: int.tryParse(_expiresController.text),
        maxViews: int.tryParse(_maxViewsController.text),
      );
      setState(() => _shareUrl = res['share_url'] as String?);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'SHARE',
    title: 'Share batch',
    notificationRoute: '/reference/agent-notifications',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        CustomerHeroCard(eyebrow: widget.batchTitle, title: 'Share this batch', subtitle: 'Generate a secure link for guests to view and place orders.'),
        const SizedBox(height: 16),
        TextFormField(controller: _expiresController, decoration: const InputDecoration(labelText: 'Expires in (days)'), keyboardType: TextInputType.number),
        const SizedBox(height: 14),
        TextFormField(controller: _maxViewsController, decoration: const InputDecoration(labelText: 'Max views (optional)'), keyboardType: TextInputType.number),
        const SizedBox(height: 20),
        FilledButton.icon(onPressed: _busy ? null : _generate, icon: const Icon(Icons.link_rounded), label: Text(_busy ? 'Generating...' : 'Generate share link')),
        if (_shareUrl != null) ...[
          const SizedBox(height: 20),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(color: appSuccess.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(14), border: Border.all(color: appSuccess)),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(children: [Icon(Icons.check_circle, color: appSuccess), SizedBox(width: 8), Text('Link generated', style: TextStyle(fontWeight: FontWeight.w800, color: appSuccess))]),
                const SizedBox(height: 10),
                SelectableText(_shareUrl!, style: const TextStyle(fontSize: 13, fontFamily: 'monospace')),
                const SizedBox(height: 12),
                OutlinedButton.icon(onPressed: () { ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Link copied'))); }, icon: const Icon(Icons.copy), label: const Text('Copy link')),
              ],
            ),
          ),
        ],
      ],
    ),
  );
}
