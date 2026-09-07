import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sahajomy_mobile/features/repository_providers.dart';

import '../../../../app/theme.dart';
import '../../../../core/ui/sahajomy_ui.dart';
import '../../../../core/utils/document_handler.dart';
import '../data/sourcing_agent_batches_repository.dart';

List<Map<String, dynamic>> _extractGoodsTypes(Map<String, dynamic>? response) {
  if (response == null) return const [];
  final categories = response['categories'] ?? response['data'] ?? const [];
  if (categories is! List) return const [];
  return [
    for (final category in categories.whereType<Map>())
      for (final type
          in ((category['goods_types'] ?? category['types'] ?? const [])
                  as List)
              .whereType<Map>())
        type.cast<String, dynamic>(),
  ].where((type) => type['id'] != null).toList();
}

class SourcingAgentCreateBatchPage extends ConsumerStatefulWidget {
  const SourcingAgentCreateBatchPage({super.key});

  @override
  ConsumerState<SourcingAgentCreateBatchPage> createState() =>
      _SourcingAgentCreateBatchPageState();
}

class _SourcingAgentCreateBatchPageState
    extends ConsumerState<SourcingAgentCreateBatchPage> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _originController = TextEditingController(text: 'Yiwu');
  final _destinationController = TextEditingController(text: 'Dar es Salaam');
  final _feeController = TextEditingController(text: '285000');
  SourcingAgentBatchesRepository get _repository =>
      ref.read(sourcingAgentBatchesRepositoryProvider);
  String _shippingMethod = 'PER_CBM';
  String _currency = 'TZS';
  var _saving = false;

  @override
  void dispose() {
    _titleController.dispose();
    _descriptionController.dispose();
    _originController.dispose();
    _destinationController.dispose();
    _feeController.dispose();
    super.dispose();
  }

  Future<void> _saveDraft() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);
    try {
      await _repository.createBatch(
        title: _titleController.text.trim(),
        description: _descriptionController.text.trim().isEmpty
            ? null
            : _descriptionController.text.trim(),
        currency: _currency,
        shippingMethod: _shippingMethod,
        shippingFeePerCbm: double.tryParse(_feeController.text),
      );
      if (!mounted) return;
      Navigator.pop(context, true);
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Unable to create this batch.')),
      );
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(
      role: 'Sourcing Agent',
      title: 'Open a sourcing batch',
    ),
    body: Form(
      key: _formKey,
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            'Create a new batch',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 6),
          const Text(
            'Set the route, shipping method, and pricing so you can begin adding products and customer orders.',
          ),
          const SizedBox(height: 20),
          SahajomySectionCard(
            title: 'Batch setup',
            children: [
              TextFormField(
                controller: _titleController,
                decoration: const InputDecoration(labelText: 'Batch title'),
                validator: (value) => (value == null || value.trim().isEmpty)
                    ? 'Enter a batch title.'
                    : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _descriptionController,
                minLines: 3,
                maxLines: 5,
                decoration: const InputDecoration(labelText: 'Description'),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: _shippingMethod,
                decoration: const InputDecoration(labelText: 'Shipping method'),
                items: const [
                  DropdownMenuItem(
                    value: 'PER_CBM',
                    child: Text('Sea Freight'),
                  ),
                  DropdownMenuItem(value: 'AIR', child: Text('Air Cargo')),
                  DropdownMenuItem(
                    value: 'EXPRESS',
                    child: Text('Express Courier'),
                  ),
                ],
                onChanged: (value) =>
                    setState(() => _shippingMethod = value ?? _shippingMethod),
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _originController,
                      decoration: const InputDecoration(labelText: 'Origin'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextFormField(
                      controller: _destinationController,
                      decoration: const InputDecoration(
                        labelText: 'Destination',
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      initialValue: _currency,
                      decoration: const InputDecoration(labelText: 'Currency'),
                      items: const [
                        DropdownMenuItem(value: 'TZS', child: Text('TZS')),
                        DropdownMenuItem(value: 'USD', child: Text('USD')),
                        DropdownMenuItem(value: 'CNY', child: Text('CNY')),
                      ],
                      onChanged: (value) =>
                          setState(() => _currency = value ?? _currency),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextFormField(
                      controller: _feeController,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Fee per CBM',
                      ),
                      validator: (value) =>
                          (double.tryParse(value ?? '') == null)
                          ? 'Enter a number.'
                          : null,
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 20),
          SahajomySectionCard(
            title: 'What happens next',
            children: const [
              Text('1. Add products to the batch catalogue.'),
              SizedBox(height: 8),
              Text(
                '2. Generate customer orders from approved product selections.',
              ),
              SizedBox(height: 8),
              Text(
                '3. Build packing lists when orders are ready for shipment.',
              ),
            ],
          ),
          const SizedBox(height: 20),
          FilledButton(
            onPressed: _saving ? null : _saveDraft,
            child: Text(_saving ? 'Creating batch...' : 'Create batch'),
          ),
        ],
      ),
    ),
  );
}

class SourcingAgentAddProductPage extends ConsumerStatefulWidget {
  const SourcingAgentAddProductPage({
    required this.batchId,
    super.key,
    this.batchTitle,
  });

  final String batchId;
  final String? batchTitle;

  @override
  ConsumerState<SourcingAgentAddProductPage> createState() =>
      _SourcingAgentAddProductPageState();
}

class _SourcingAgentAddProductPageState
    extends ConsumerState<SourcingAgentAddProductPage> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _imageUrlController = TextEditingController();
  final _priceController = TextEditingController();
  final _minOrderController = TextEditingController(text: '1');
  SourcingAgentBatchesRepository get _repository =>
      ref.read(sourcingAgentBatchesRepositoryProvider);
  late Future<Map<String, dynamic>> _goodsCategories = Future.microtask(
    () => _repository.listGoodsCategories(),
  );
  String? _goodsTypeId;
  var _saving = false;

  @override
  void initState() {
    super.initState();
    _imageUrlController.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _nameController.dispose();
    _imageUrlController.dispose();
    _priceController.dispose();
    _minOrderController.dispose();
    super.dispose();
  }

  Future<void> _saveProduct() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);
    try {
      await _repository.createProduct(
        batchId: widget.batchId,
        goodsTypeId: _goodsTypeId!,
        name: _nameController.text.trim(),
        pricePerUnit: double.parse(_priceController.text),
        minimumOrderQuantity: int.parse(_minOrderController.text),
        imageUrl: _imageUrlController.text.trim(),
      );
      if (!mounted) return;
      Navigator.pop(context, true);
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Unable to add this product.')),
      );
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(
      role: 'Sourcing Agent',
      title: 'Add a batch product',
    ),
    body: Form(
      key: _formKey,
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            widget.batchTitle ?? 'Batch product',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 6),
          const Text(
            'Prepare the product card used for order generation and financial review.',
          ),
          const SizedBox(height: 20),
          SahajomySectionCard(
            title: 'Product details',
            children: [
              TextFormField(
                controller: _nameController,
                decoration: const InputDecoration(labelText: 'Product name'),
                validator: (value) => (value == null || value.trim().isEmpty)
                    ? 'Enter a product name.'
                    : null,
              ),
              const SizedBox(height: 12),
              FutureBuilder<Map<String, dynamic>>(
                future: _goodsCategories,
                builder: (context, snapshot) {
                  if (snapshot.connectionState != ConnectionState.done) {
                    return const LinearProgressIndicator();
                  }
                  final types = _extractGoodsTypes(snapshot.data);
                  if (snapshot.hasError || types.isEmpty) {
                    return OutlinedButton(
                      onPressed: () => setState(
                        () => _goodsCategories = _repository
                            .listGoodsCategories(),
                      ),
                      child: const Text('Retry loading goods types'),
                    );
                  }
                  return DropdownButtonFormField<String>(
                    initialValue: _goodsTypeId,
                    decoration: const InputDecoration(labelText: 'Goods type'),
                    items: types
                        .map(
                          (type) => DropdownMenuItem(
                            value: '${type['id']}',
                            child: Text('${type['name'] ?? 'Goods type'}'),
                          ),
                        )
                        .toList(),
                    onChanged: (value) => setState(() => _goodsTypeId = value),
                    validator: (value) =>
                        value == null ? 'Select a goods type.' : null,
                  );
                },
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _imageUrlController,
                keyboardType: TextInputType.url,
                decoration: const InputDecoration(
                  labelText: 'Product image URL',
                  helperText: 'Paste a direct image link — preview appears below.',
                ),
                validator: (value) =>
                    value == null ||
                        Uri.tryParse(value)?.hasAbsolutePath != true
                    ? 'Enter a valid image URL.'
                    : null,
              ),
              const SizedBox(height: 16),
              _ImagePreview(url: _imageUrlController.text.trim()),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _priceController,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Customer price',
                      ),
                      validator: (value) =>
                          (double.tryParse(value ?? '') == null)
                          ? 'Enter a valid amount.'
                          : null,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextFormField(
                      controller: _minOrderController,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Minimum order',
                      ),
                      validator: (value) => (int.tryParse(value ?? '') == null)
                          ? 'Enter a whole number.'
                          : null,
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 20),
          FilledButton(
            onPressed: _saving ? null : _saveProduct,
            child: Text(_saving ? 'Adding product...' : 'Add product'),
          ),
        ],
      ),
    ),
  );
}

class _ImagePreview extends StatelessWidget {
  const _ImagePreview({required this.url});
  final String url;

  @override
  Widget build(BuildContext context) {
    if (url.isEmpty || Uri.tryParse(url)?.hasAbsolutePath != true) {
      return Container(
        height: 200,
        width: double.infinity,
        decoration: BoxDecoration(
          color: appCanvas,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: appBorder),
        ),
        child: const Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.image_outlined, size: 44, color: appMuted),
              SizedBox(height: 8),
              Text('Image preview', style: TextStyle(color: appMuted, fontSize: 13)),
            ],
          ),
        ),
      );
    }
    return ClipRRect(
      borderRadius: BorderRadius.circular(12),
      child: Image.network(
        url,
        height: 220,
        width: double.infinity,
        fit: BoxFit.cover,
        errorBuilder: (context, error, stackTrace) => Container(
          height: 200,
          width: double.infinity,
          color: appCanvas,
          child: const Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.broken_image_outlined, size: 40, color: appMuted),
                SizedBox(height: 8),
                Text('Could not load image', style: TextStyle(color: appMuted, fontSize: 13)),
              ],
            ),
          ),
        ),
        loadingBuilder: (context, child, progress) {
          if (progress == null) return child;
          return Container(
            height: 200,
            color: appCanvas,
            child: Center(
              child: CircularProgressIndicator(
                value: progress.expectedTotalBytes != null
                    ? progress.cumulativeBytesLoaded /
                        progress.expectedTotalBytes!
                    : null,
                color: brandCoral,
              ),
            ),
          );
        },
      ),
    );
  }
}

class SourcingAgentGenerateOrdersPage extends ConsumerStatefulWidget {
  const SourcingAgentGenerateOrdersPage({
    required this.batchId,
    super.key,
    this.batchTitle,
  });

  final String batchId;
  final String? batchTitle;

  @override
  ConsumerState<SourcingAgentGenerateOrdersPage> createState() =>
      _SourcingAgentGenerateOrdersPageState();
}

class _SourcingAgentGenerateOrdersPageState
    extends ConsumerState<SourcingAgentGenerateOrdersPage> {
  SourcingAgentBatchesRepository get _repository =>
      ref.read(sourcingAgentBatchesRepositoryProvider);
  late Future<List<Map<String, dynamic>>> _data = Future.microtask(
    () => _load(),
  );

  Future<List<Map<String, dynamic>>> _load() => Future.wait([
    _repository.getBatch(widget.batchId),
    _repository.listOrders(widget.batchId),
  ]);

  void _retry() => setState(() => _data = _load());

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(
      role: 'Sourcing Agent',
      title: 'Generate customer orders',
    ),
    body: FutureBuilder<List<Map<String, dynamic>>>(
      future: _data,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return SahajomyMessageState(
            icon: Icons.wifi_off_rounded,
            message: 'Orders are unavailable right now.',
            actionLabel: 'Try again',
            onAction: _retry,
          );
        }

        final batch = snapshot.data![0];
        final orders = (snapshot.data![1]['orders'] as List? ?? const [])
            .cast<Map<String, dynamic>>();

        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              widget.batchTitle ??
                  batch['title'] as String? ??
                  'Customer orders',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 6),
            const Text(
              'Review the order set before downstream packing-list and financial actions.',
            ),
            const SizedBox(height: 20),
            SahajomySectionCard(
              title: 'Batch snapshot',
              children: [
                SahajomyKeyValueList(
                  entries: {
                    'status': batch['status'],
                    'shipping_method': batch['shipping_method'],
                    'total_orders': orders.length,
                    'currency': batch['currency'],
                  },
                ),
              ],
            ),
            const SizedBox(height: 20),
            if (orders.isEmpty)
              const SahajomySectionCard(
                title: 'No orders yet',
                children: [
                  Text(
                    'Products can be added now, then orders will appear here after customers check out.',
                  ),
                ],
              ),
            for (final order in orders) ...[
              Card(
                child: ListTile(
                  leading: const CircleAvatar(
                    child: Icon(Icons.shopping_bag_outlined),
                  ),
                  title: Text(
                    order['order_reference'] as String? ?? 'Order',
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                  subtitle: Text(
                    '${order['customer_name'] ?? 'Customer'} • ${order['payment_status'] ?? 'Pending payment'}',
                  ),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: () => Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => SourcingAgentOrderDetailPage(
                        batchTitle:
                            widget.batchTitle ?? batch['title'] as String?,
                        order: order,
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 10),
            ],
          ],
        );
      },
    ),
  );
}

class SourcingAgentBatchFinancialsPage extends ConsumerStatefulWidget {
  const SourcingAgentBatchFinancialsPage({required this.batchId, super.key});

  final String batchId;

  @override
  ConsumerState<SourcingAgentBatchFinancialsPage> createState() =>
      _SourcingAgentBatchFinancialsPageState();
}

class _SourcingAgentBatchFinancialsPageState
    extends ConsumerState<SourcingAgentBatchFinancialsPage> {
  SourcingAgentBatchesRepository get _repository =>
      ref.read(sourcingAgentBatchesRepositoryProvider);
  late Future<List<Map<String, dynamic>>> _data = Future.microtask(
    () => _load(),
  );

  Future<List<Map<String, dynamic>>> _load() => Future.wait([
    _repository.getBatch(widget.batchId),
    _repository.listOrders(widget.batchId),
  ]);

  void _retry() => setState(() => _data = _load());

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(
      role: 'Sourcing Agent',
      title: 'Batch financials',
    ),
    body: FutureBuilder<List<Map<String, dynamic>>>(
      future: _data,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return SahajomyMessageState(
            icon: Icons.wifi_off_rounded,
            message: 'Financials are unavailable right now.',
            actionLabel: 'Try again',
            onAction: _retry,
          );
        }

        final batch = snapshot.data![0];
        final orders = (snapshot.data![1]['orders'] as List? ?? const [])
            .cast<Map<String, dynamic>>();
        final currency = '${batch['currency'] ?? 'TZS'}';
        final revenue = _readAmount(batch['total_revenue']) > 0
            ? _readAmount(batch['total_revenue'])
            : orders.fold<double>(
                0,
                (sum, order) => sum + _readAmount(order['total_amount']),
              );
        final netEarnings = _readAmount(batch['net_earnings']);
        final paid = orders
            .where(
              (order) =>
                  '${order['payment_status']}'.toLowerCase().contains('paid'),
            )
            .length;
        final pending = orders.length - paid;

        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              batch['title'] as String? ?? 'Batch financials',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 6),
            const Text(
              'Review totals, payment state, and customer-by-customer revenue exposure.',
            ),
            const SizedBox(height: 20),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                SahajomyMetricTile(
                  label: 'Revenue',
                  value: _formatMoney(currency, revenue),
                ),
                SahajomyMetricTile(
                  label: 'Net earnings',
                  value: _formatMoney(currency, netEarnings),
                ),
                SahajomyMetricTile(label: 'Paid orders', value: paid),
                SahajomyMetricTile(label: 'Pending payment', value: pending),
              ],
            ),
            const SizedBox(height: 24),
            SahajomySectionCard(
              title: 'Batch totals',
              children: [
                SahajomyKeyValueList(
                  entries: {
                    'shipping_fee_per_cbm': _formatMoney(
                      currency,
                      _readAmount(batch['shipping_fee_per_cbm']),
                    ),
                    'order_count': batch['order_count'] ?? orders.length,
                    'product_count': batch['total_products'],
                    'status': batch['status'],
                  },
                ),
              ],
            ),
            const SizedBox(height: 20),
            SahajomySectionCard(
              title: 'Customer payment status',
              children: [
                if (orders.isEmpty)
                  const Text('No orders are available for this batch yet.'),
                for (final order in orders) ...[
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(
                      order['customer_name'] as String? ?? 'Customer',
                    ),
                    subtitle: Text(
                      order['order_reference'] as String? ?? 'Order',
                    ),
                    trailing: SahajomyStatusPill(
                      label: '${order['payment_status'] ?? 'Pending'}',
                    ),
                  ),
                ],
              ],
            ),
          ],
        );
      },
    ),
  );
}

class SourcingAgentPackingListCreatePage extends ConsumerStatefulWidget {
  const SourcingAgentPackingListCreatePage({
    required this.batchId,
    super.key,
    this.batchTitle,
  });

  final String batchId;
  final String? batchTitle;

  @override
  ConsumerState<SourcingAgentPackingListCreatePage> createState() =>
      _SourcingAgentPackingListCreatePageState();
}

class _SourcingAgentPackingListCreatePageState
    extends ConsumerState<SourcingAgentPackingListCreatePage> {
  SourcingAgentBatchesRepository get _repository =>
      ref.read(sourcingAgentBatchesRepositoryProvider);
  final _cartonsController = TextEditingController(text: '12');
  final _weightController = TextEditingController(text: '180');
  late Future<List<Map<String, dynamic>>> _data = Future.microtask(
    () => _load(),
  );
  final Set<String> _selectedOrders = <String>{};
  var _generating = false;

  Future<List<Map<String, dynamic>>> _load() => Future.wait([
    _repository.getBatch(widget.batchId),
    _repository.listOrders(widget.batchId),
  ]);

  void _retry() => setState(() => _data = _load());

  @override
  void dispose() {
    _cartonsController.dispose();
    _weightController.dispose();
    super.dispose();
  }

  Future<void> _generate() async {
    setState(() => _generating = true);
    try {
      await _repository.createPackingList(
        batchId: widget.batchId,
        name: '${widget.batchTitle ?? 'Batch'} packing list',
        description:
            '${_selectedOrders.length} selected orders · ${_cartonsController.text} cartons · ${_weightController.text} kg',
      );
      if (!mounted) return;
      Navigator.pop(context, true);
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Unable to create the packing list.')),
      );
    } finally {
      if (mounted) setState(() => _generating = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(
      role: 'Sourcing Agent',
      title: 'Create packing list',
    ),
    body: FutureBuilder<List<Map<String, dynamic>>>(
      future: _data,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return SahajomyMessageState(
            icon: Icons.wifi_off_rounded,
            message: 'Packing-list preparation is unavailable right now.',
            actionLabel: 'Try again',
            onAction: _retry,
          );
        }

        final batch = snapshot.data![0];
        final orders = (snapshot.data![1]['orders'] as List? ?? const [])
            .cast<Map<String, dynamic>>();

        for (final order in orders.take(1)) {
          _selectedOrders.add(
            '${order['id'] ?? order['order_reference'] ?? order.hashCode}',
          );
        }

        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              widget.batchTitle ?? batch['title'] as String? ?? 'Packing list',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 6),
            const Text(
              'Choose the included orders, then confirm carton and weight totals before export.',
            ),
            const SizedBox(height: 20),
            SahajomySectionCard(
              title: 'Select orders',
              children: [
                if (orders.isEmpty)
                  const Text(
                    'Orders will appear here after customers place them.',
                  ),
                for (final order in orders)
                  CheckboxListTile(
                    value: _selectedOrders.contains(
                      '${order['id'] ?? order['order_reference'] ?? order.hashCode}',
                    ),
                    onChanged: (value) {
                      final key =
                          '${order['id'] ?? order['order_reference'] ?? order.hashCode}';
                      setState(() {
                        if (value == true) {
                          _selectedOrders.add(key);
                        } else {
                          _selectedOrders.remove(key);
                        }
                      });
                    },
                    title: Text(order['order_reference'] as String? ?? 'Order'),
                    subtitle: Text(
                      order['customer_name'] as String? ?? 'Customer',
                    ),
                    controlAffinity: ListTileControlAffinity.leading,
                    contentPadding: EdgeInsets.zero,
                  ),
              ],
            ),
            const SizedBox(height: 20),
            SahajomySectionCard(
              title: 'Cargo totals',
              children: [
                Row(
                  children: [
                    Expanded(
                      child: TextFormField(
                        controller: _cartonsController,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(labelText: 'Cartons'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextFormField(
                        controller: _weightController,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(
                          labelText: 'Weight (kg)',
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 20),
            FilledButton(
              onPressed: orders.isEmpty || _generating ? null : _generate,
              child: Text(
                _generating
                    ? 'Creating packing list...'
                    : 'Create packing list',
              ),
            ),
          ],
        );
      },
    ),
  );
}

class SourcingAgentPackingListListPage extends ConsumerStatefulWidget {
  const SourcingAgentPackingListListPage({super.key, this.initialPackingLists});

  final List<Map<String, dynamic>>? initialPackingLists;

  @override
  ConsumerState<SourcingAgentPackingListListPage> createState() =>
      _SourcingAgentPackingListListPageState();
}

class _SourcingAgentPackingListListPageState
    extends ConsumerState<SourcingAgentPackingListListPage> {
  SourcingAgentBatchesRepository get _repository =>
      ref.read(sourcingAgentBatchesRepositoryProvider);
  late Future<Map<String, dynamic>> _packingLists = Future.microtask(
    () => widget.initialPackingLists == null
        ? _repository.listPackingLists()
        : Future.value({'packing_lists': widget.initialPackingLists}),
  );

  void _retry() =>
      setState(() => _packingLists = _repository.listPackingLists());

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(
      role: 'Sourcing Agent',
      title: 'Packing lists',
    ),
    body: FutureBuilder<Map<String, dynamic>>(
      future: _packingLists,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return SahajomyMessageState(
            icon: Icons.wifi_off_rounded,
            message: 'Packing-list records are unavailable right now.',
            actionLabel: 'Try again',
            onAction: _retry,
          );
        }

        final lists = (snapshot.data!['packing_lists'] as List? ??
                snapshot.data!['data'] as List? ??
                const [])
            .cast<Map<String, dynamic>>();

        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              'Packing lists',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 6),
            const Text(
              'Review generated sourcing documents and open a packing list to manage items or export.',
            ),
            const SizedBox(height: 20),
            if (lists.isEmpty)
              const SahajomySectionCard(
                title: 'No packing lists yet',
                children: [
                  Text(
                    'Create a packing list from a batch to get started.',
                  ),
                ],
              ),
            for (final pl in lists) ...[
              Card(
                child: ListTile(
                  leading: const CircleAvatar(
                    child: Icon(Icons.description_outlined),
                  ),
                  title: Text(
                    pl['name'] as String? ??
                        pl['packing_list_number'] as String? ??
                        'Packing list',
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                  subtitle: Text(
                    pl['packing_list_number'] as String? ??
                        '${pl['items_count'] ?? pl['item_count'] ?? 0} items',
                  ),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: () => Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => SourcingAgentPackingListDetailPage(
                        packingListId: '${pl['id']}',
                        batchTitle: pl['batch_title'] as String?,
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 10),
            ],
          ],
        );
      },
    ),
  );
}

class SourcingAgentPackingListDetailPage extends ConsumerStatefulWidget {
  const SourcingAgentPackingListDetailPage({
    required this.packingListId,
    super.key,
    this.batchId,
    this.batchTitle,
  });

  final String packingListId;
  final String? batchId;
  final String? batchTitle;

  @override
  ConsumerState<SourcingAgentPackingListDetailPage> createState() =>
      _SourcingAgentPackingListDetailPageState();
}

class _SourcingAgentPackingListDetailPageState
    extends ConsumerState<SourcingAgentPackingListDetailPage> {
  SourcingAgentBatchesRepository get _repository =>
      ref.read(sourcingAgentBatchesRepositoryProvider);

  Map<String, dynamic>? _packingList;
  bool _loading = true;
  String? _error;
  bool _exporting = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await _repository.getPackingList(widget.packingListId);
      if (!mounted) return;
      setState(() {
        _packingList = data;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'Unable to load the packing list. Pull down to retry.';
        _loading = false;
      });
    }
  }

  Future<void> _exportPdf() async {
    final pl = _packingList;
    if (pl == null) return;
    final name = (pl['packing_list_number'] as String?) ??
        (pl['name'] as String?) ??
        'packing-list';
    setState(() => _exporting = true);
    try {
      final bytes = await _repository.exportPackingListPdf(widget.packingListId);
      await DocumentHandler.saveAndOpen(
        bytes: bytes,
        fileName: '$name.pdf',
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Unable to download the PDF.')),
      );
    } finally {
      if (mounted) setState(() => _exporting = false);
    }
  }

  Future<void> _exportExcel() async {
    final pl = _packingList;
    if (pl == null) return;
    final name = (pl['packing_list_number'] as String?) ??
        (pl['name'] as String?) ??
        'packing-list';
    setState(() => _exporting = true);
    try {
      final bytes = await _repository.exportPackingListExcel(widget.packingListId);
      await DocumentHandler.saveAndOpen(
        bytes: bytes,
        fileName: '$name.xlsx',
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Unable to download the spreadsheet.')),
      );
    } finally {
      if (mounted) setState(() => _exporting = false);
    }
  }

  Future<void> _share() async {
    final pl = _packingList;
    if (pl == null) return;
    final name = (pl['packing_list_number'] as String?) ??
        (pl['name'] as String?) ??
        'packing-list';
    setState(() => _exporting = true);
    try {
      final bytes = await _repository.exportPackingListPdf(widget.packingListId);
      await DocumentHandler.saveAndShare(
        bytes: bytes,
        fileName: '$name.pdf',
        subject: name,
        text: 'Packing list: $name',
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Unable to share the packing list.')),
      );
    } finally {
      if (mounted) setState(() => _exporting = false);
    }
  }

  Future<void> _addItem() async {
    final result = await showModalBottomSheet<Map<String, dynamic>>(
      context: context,
      isScrollControlled: true,
      builder: (_) => const _PackingListItemSheet(),
    );
    if (result == null) return;
    try {
      await _repository.addPackingListItem(
        packingListId: widget.packingListId,
        itemName: result['item_name'] as String,
        pricePerPiece: result['price_per_piece'] as double,
        cartons: result['cartons'] as int,
        itemsPerCarton: result['items_per_carton'] as int,
        cbmPerCarton: result['cbm_per_carton'] as double,
        kilogramPerCarton: result['kilogram_per_carton'] as double,
        itemCode: result['item_code'] as String?,
        itemPicture: result['item_picture'] as String?,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Item added.')),
      );
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Unable to add the item.')),
      );
    }
  }

  Future<void> _editItem(Map<String, dynamic> item) async {
    final itemId = '${item['id']}';
    final result = await showModalBottomSheet<Map<String, dynamic>>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _PackingListItemSheet(initial: item),
    );
    if (result == null) return;
    try {
      await _repository.updatePackingListItem(
        itemId: itemId,
        itemName: result['item_name'] as String?,
        pricePerPiece: result['price_per_piece'] as double?,
        cartons: result['cartons'] as int?,
        itemsPerCarton: result['items_per_carton'] as int?,
        cbmPerCarton: result['cbm_per_carton'] as double?,
        kilogramPerCarton: result['kilogram_per_carton'] as double?,
        itemCode: result['item_code'] as String?,
        itemPicture: result['item_picture'] as String?,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Item updated.')),
      );
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Unable to update the item.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: SahajomyScreenHeader(
        role: 'Sourcing Agent',
        title: 'Packing list',
        actions: [
          IconButton(
            tooltip: 'Share',
            onPressed: _exporting ? null : _share,
            icon: const Icon(Icons.share_outlined),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
          ? RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                children: [
                  SizedBox(height: MediaQuery.of(context).size.height * 0.3),
                  Padding(
                    padding: const EdgeInsets.all(24),
                    child: Text(_error!, textAlign: TextAlign.center),
                  ),
                ],
              ),
            )
          : _buildBody(theme),
    );
  }

  Widget _buildBody(ThemeData theme) {
    final pl = _packingList!;
    final items = (pl['items'] as List? ?? const [])
        .cast<Map<String, dynamic>>();
    final number = pl['packing_list_number'] as String?;
    final name = pl['name'] as String?;
    final qrUrl = pl['qr_code_url'] as String?;
    final agentName = pl['agent_name'] as String?;
    final agentPhone = pl['agent_phone_or_whatsapp'] as String?;
    final agentInstagram = pl['agent_instagram'] as String?;
    final agentTiktok = pl['agent_tiktok'] as String?;

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            name ?? number ?? 'Packing list',
            style: theme.textTheme.headlineMedium,
          ),
          if (number != null) ...[
            const SizedBox(height: 4),
            Text(
              number,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.primary,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
          if (widget.batchTitle != null) ...[
            const SizedBox(height: 4),
            Text('Batch: ${widget.batchTitle}'),
          ],
          const SizedBox(height: 20),
          if (qrUrl != null && qrUrl.isNotEmpty)
            SahajomySectionCard(
              title: 'QR code',
              children: [
                Center(
                  child: Image.network(
                    qrUrl,
                    width: 160,
                    height: 160,
                    errorBuilder: (_, _, _) => const SizedBox(
                      width: 160,
                      height: 160,
                      child: Icon(Icons.qr_code_2, size: 96),
                    ),
                  ),
                ),
              ],
            ),
          if (agentName != null || agentPhone != null) ...[
            const SizedBox(height: 12),
            SahajomySectionCard(
              title: 'Agent details',
              children: [
                SahajomyKeyValueList(entries: {
                  'Name': ?agentName,
                  'Phone / WhatsApp': ?agentPhone,
                  'Instagram': ?agentInstagram,
                  'TikTok': ?agentTiktok,
                }),
              ],
            ),
          ],
          const SizedBox(height: 20),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _exporting ? null : _exportPdf,
                  icon: const Icon(Icons.picture_as_pdf_outlined),
                  label: const Text('PDF'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _exporting ? null : _exportExcel,
                  icon: const Icon(Icons.table_chart_outlined),
                  label: const Text('Excel'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          SahajomySectionCard(
            title: 'Items (${items.length})',
            children: [
              if (items.isEmpty)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 12),
                  child: Text('No items yet. Tap "Add item" to start.'),
                ),
              for (final item in items) _buildItemTile(item, theme),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: _exporting ? null : _addItem,
                  icon: const Icon(Icons.add),
                  label: const Text('Add item'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Widget _buildItemTile(Map<String, dynamic> item, ThemeData theme) {
    final picture = item['item_picture'] as String?;
    final name = item['item_name'] as String? ?? 'Item';
    final code = item['item_code'] as String?;
    final price = _readAmount(item['price_per_piece']);
    final cartons = _asInt(item['cartons']);
    final perCarton = _asInt(item['items_per_carton']);
    final cbm = _readAmount(item['cbm_per_carton']);
    final kg = _readAmount(item['kilogram_per_carton']);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (picture != null && picture.isNotEmpty)
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Image.network(
                picture,
                width: 56,
                height: 56,
                fit: BoxFit.cover,
                errorBuilder: (_, _, _) => Container(
                  width: 56,
                  height: 56,
                  color: theme.colorScheme.surfaceContainerHighest,
                  child: const Icon(Icons.image_not_supported_outlined),
                ),
              ),
            )
          else
            Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                color: theme.colorScheme.surfaceContainerHighest,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(Icons.inventory_2_outlined),
            ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name, style: const TextStyle(fontWeight: FontWeight.w600)),
                if (code != null && code.isNotEmpty)
                  Text('Code: $code', style: theme.textTheme.bodySmall),
                const SizedBox(height: 4),
                Wrap(
                  spacing: 12,
                  runSpacing: 4,
                  children: [
                    Text('$cartons cartons'),
                    Text('$perCarton pcs/carton'),
                    Text('${cbm.toStringAsFixed(4)} CBM'),
                    Text('${kg.toStringAsFixed(1)} kg'),
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  '${price.toStringAsFixed(2)} / piece',
                  style: TextStyle(
                    color: theme.colorScheme.primary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
          IconButton(
            tooltip: 'Edit item',
            onPressed: () => _editItem(item),
            icon: const Icon(Icons.edit_outlined, size: 20),
          ),
        ],
      ),
    );
  }
}

/// Form sheet for adding/editing a packing list item.
class _PackingListItemSheet extends StatefulWidget {
  const _PackingListItemSheet({this.initial});

  final Map<String, dynamic>? initial;

  @override
  State<_PackingListItemSheet> createState() => _PackingListItemSheetState();
}

class _PackingListItemSheetState extends State<_PackingListItemSheet> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _name;
  late final TextEditingController _code;
  late final TextEditingController _price;
  late final TextEditingController _cartons;
  late final TextEditingController _perCarton;
  late final TextEditingController _cbm;
  late final TextEditingController _kg;
  late final TextEditingController _picture;

  @override
  void initState() {
    super.initState();
    final i = widget.initial;
    _name = TextEditingController(text: i?['item_name'] as String? ?? '');
    _code = TextEditingController(text: i?['item_code'] as String? ?? '');
    _price = TextEditingController(
      text: i == null ? '' : '${i['price_per_piece'] ?? ''}',
    );
    _cartons = TextEditingController(
      text: i == null ? '' : '${i['cartons'] ?? ''}',
    );
    _perCarton = TextEditingController(
      text: i == null ? '' : '${i['items_per_carton'] ?? ''}',
    );
    _cbm = TextEditingController(
      text: i == null ? '' : '${i['cbm_per_carton'] ?? ''}',
    );
    _kg = TextEditingController(
      text: i == null ? '' : '${i['kilogram_per_carton'] ?? ''}',
    );
    _picture = TextEditingController(text: i?['item_picture'] as String? ?? '');
  }

  @override
  void dispose() {
    _name.dispose();
    _code.dispose();
    _price.dispose();
    _cartons.dispose();
    _perCarton.dispose();
    _cbm.dispose();
    _kg.dispose();
    _picture.dispose();
    super.dispose();
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    Navigator.pop(context, {
      'item_name': _name.text.trim(),
      'item_code': _code.text.trim().isEmpty ? null : _code.text.trim(),
      'item_picture': _picture.text.trim().isEmpty ? null : _picture.text.trim(),
      'price_per_piece': double.tryParse(_price.text.trim()) ?? 0,
      'cartons': int.tryParse(_cartons.text.trim()) ?? 0,
      'items_per_carton': int.tryParse(_perCarton.text.trim()) ?? 0,
      'cbm_per_carton': double.tryParse(_cbm.text.trim()) ?? 0,
      'kilogram_per_carton': double.tryParse(_kg.text.trim()) ?? 0,
    });
  }

  @override
  Widget build(BuildContext context) {
    final padding = EdgeInsets.only(
      left: 20,
      right: 20,
      top: 12,
      bottom: MediaQuery.of(context).viewInsets.bottom + 20,
    );
    return SingleChildScrollView(
      padding: padding,
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              widget.initial == null ? 'Add item' : 'Edit item',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _name,
              decoration: const InputDecoration(labelText: 'Item name *'),
              validator: (v) =>
                  (v == null || v.trim().isEmpty) ? 'Required' : null,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _code,
              decoration: const InputDecoration(labelText: 'Item code'),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _picture,
              decoration: const InputDecoration(labelText: 'Picture URL'),
              keyboardType: TextInputType.url,
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: _price,
                    decoration: const InputDecoration(labelText: 'Price / piece *'),
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    validator: (v) => double.tryParse(v ?? '') == null
                        ? 'Enter a number'
                        : null,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextFormField(
                    controller: _cartons,
                    decoration: const InputDecoration(labelText: 'Cartons *'),
                    keyboardType: TextInputType.number,
                    validator: (v) =>
                        int.tryParse(v ?? '') == null ? 'Enter a number' : null,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: _perCarton,
                    decoration: const InputDecoration(labelText: 'Items / carton *'),
                    keyboardType: TextInputType.number,
                    validator: (v) =>
                        int.tryParse(v ?? '') == null ? 'Enter a number' : null,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextFormField(
                    controller: _cbm,
                    decoration: const InputDecoration(labelText: 'CBM / carton *'),
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    validator: (v) => double.tryParse(v ?? '') == null
                        ? 'Enter a number'
                        : null,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _kg,
              decoration: const InputDecoration(labelText: 'Kilograms / carton *'),
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              validator: (v) =>
                  double.tryParse(v ?? '') == null ? 'Enter a number' : null,
            ),
            const SizedBox(height: 20),
            FilledButton(onPressed: _submit, child: const Text('Save item')),
          ],
        ),
      ),
    );
  }
}

class SourcingAgentOrderDetailPage extends StatelessWidget {
  const SourcingAgentOrderDetailPage({
    required this.order,
    super.key,
    this.batchTitle,
  });

  final Map<String, dynamic> order;
  final String? batchTitle;

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(
      role: 'Sourcing Agent',
      title: 'Order details',
    ),
    body: ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Text(
          order['order_reference'] as String? ?? 'Order details',
          style: Theme.of(context).textTheme.headlineMedium,
        ),
        const SizedBox(height: 6),
        Text(
          batchTitle == null
              ? 'Review payment and delivery state for this customer order.'
              : 'Part of $batchTitle.',
        ),
        const SizedBox(height: 20),
        SahajomySectionCard(
          title: 'Order summary',
          children: [
            SahajomyKeyValueList(
              entries: {
                'customer_name': order['customer_name'],
                'payment_status': order['payment_status'],
                'delivery_status': order['delivery_status'],
                'total_amount': order['total_amount'],
                'currency': order['currency'],
              },
            ),
          ],
        ),
      ],
    ),
  );
}

double _readAmount(Object? value) {
  if (value is double) return value;
  if (value is int) return value.toDouble();
  if (value is num) return value.toDouble();
  return double.tryParse('$value') ?? 0;
}

String _formatMoney(String currency, double value) =>
    '$currency ${value.toStringAsFixed(value.truncateToDouble() == value ? 0 : 2)}';

int _asInt(Object? value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  return int.tryParse('$value') ?? 0;
}
