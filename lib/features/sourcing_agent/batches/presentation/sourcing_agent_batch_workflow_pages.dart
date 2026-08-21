import 'package:flutter/material.dart';

import '../../../../core/ui/sahajomy_ui.dart';
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

class SourcingAgentCreateBatchPage extends StatefulWidget {
  const SourcingAgentCreateBatchPage({super.key});

  @override
  State<SourcingAgentCreateBatchPage> createState() =>
      _SourcingAgentCreateBatchPageState();
}

class _SourcingAgentCreateBatchPageState
    extends State<SourcingAgentCreateBatchPage> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _originController = TextEditingController(text: 'Yiwu');
  final _destinationController = TextEditingController(text: 'Dar es Salaam');
  final _feeController = TextEditingController(text: '285000');
  final _repository = SourcingAgentBatchesRepository();
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

class SourcingAgentAddProductPage extends StatefulWidget {
  const SourcingAgentAddProductPage({
    required this.batchId,
    super.key,
    this.batchTitle,
  });

  final String batchId;
  final String? batchTitle;

  @override
  State<SourcingAgentAddProductPage> createState() =>
      _SourcingAgentAddProductPageState();
}

class _SourcingAgentAddProductPageState
    extends State<SourcingAgentAddProductPage> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _imageUrlController = TextEditingController();
  final _priceController = TextEditingController();
  final _minOrderController = TextEditingController(text: '1');
  final _repository = SourcingAgentBatchesRepository();
  late Future<Map<String, dynamic>> _goodsCategories = _repository
      .listGoodsCategories();
  String? _goodsTypeId;
  var _saving = false;

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
                ),
                validator: (value) =>
                    value == null ||
                        Uri.tryParse(value)?.hasAbsolutePath != true
                    ? 'Enter a valid image URL.'
                    : null,
              ),
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

class SourcingAgentGenerateOrdersPage extends StatefulWidget {
  const SourcingAgentGenerateOrdersPage({
    required this.batchId,
    super.key,
    this.batchTitle,
  });

  final String batchId;
  final String? batchTitle;

  @override
  State<SourcingAgentGenerateOrdersPage> createState() =>
      _SourcingAgentGenerateOrdersPageState();
}

class _SourcingAgentGenerateOrdersPageState
    extends State<SourcingAgentGenerateOrdersPage> {
  final _repository = SourcingAgentBatchesRepository();
  late Future<List<Map<String, dynamic>>> _data = _load();

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

class SourcingAgentBatchFinancialsPage extends StatefulWidget {
  const SourcingAgentBatchFinancialsPage({required this.batchId, super.key});

  final String batchId;

  @override
  State<SourcingAgentBatchFinancialsPage> createState() =>
      _SourcingAgentBatchFinancialsPageState();
}

class _SourcingAgentBatchFinancialsPageState
    extends State<SourcingAgentBatchFinancialsPage> {
  final _repository = SourcingAgentBatchesRepository();
  late Future<List<Map<String, dynamic>>> _data = _load();

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

class SourcingAgentPackingListCreatePage extends StatefulWidget {
  const SourcingAgentPackingListCreatePage({
    required this.batchId,
    super.key,
    this.batchTitle,
  });

  final String batchId;
  final String? batchTitle;

  @override
  State<SourcingAgentPackingListCreatePage> createState() =>
      _SourcingAgentPackingListCreatePageState();
}

class _SourcingAgentPackingListCreatePageState
    extends State<SourcingAgentPackingListCreatePage> {
  final _repository = SourcingAgentBatchesRepository();
  final _cartonsController = TextEditingController(text: '12');
  final _weightController = TextEditingController(text: '180');
  late Future<List<Map<String, dynamic>>> _data = _load();
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

class SourcingAgentPackingListListPage extends StatefulWidget {
  const SourcingAgentPackingListListPage({super.key, this.initialBatches});

  final List<Map<String, dynamic>>? initialBatches;

  @override
  State<SourcingAgentPackingListListPage> createState() =>
      _SourcingAgentPackingListListPageState();
}

class _SourcingAgentPackingListListPageState
    extends State<SourcingAgentPackingListListPage> {
  final _repository = SourcingAgentBatchesRepository();
  late Future<Map<String, dynamic>> _batches = widget.initialBatches == null
      ? _repository.listBatches()
      : Future.value({'batches': widget.initialBatches});

  void _retry() => setState(() => _batches = _repository.listBatches());

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(
      role: 'Sourcing Agent',
      title: 'Packing lists',
    ),
    body: FutureBuilder<Map<String, dynamic>>(
      future: _batches,
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

        final batches = (snapshot.data!['batches'] as List? ?? const [])
            .cast<Map<String, dynamic>>()
            .where((batch) => _asInt(batch['total_orders']) > 0)
            .toList();

        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              'Packing lists',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 6),
            const Text(
              'Review generated sourcing documents and open the latest ready-to-ship batch.',
            ),
            const SizedBox(height: 20),
            if (batches.isEmpty)
              const SahajomySectionCard(
                title: 'No packing lists yet',
                children: [
                  Text(
                    'Packing lists will be available after orders are confirmed inside a batch.',
                  ),
                ],
              ),
            for (final batch in batches) ...[
              Card(
                child: ListTile(
                  leading: const CircleAvatar(
                    child: Icon(Icons.description_outlined),
                  ),
                  title: Text(
                    batch['title'] as String? ?? 'Packing list',
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                  subtitle: Text(
                    '${_asInt(batch['total_orders'])} orders • ${_asInt(batch['total_products'])} products',
                  ),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: () => Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => SourcingAgentPackingListDetailPage(
                        batchId: '${batch['id']}',
                        batchTitle: batch['title'] as String?,
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

class SourcingAgentPackingListDetailPage extends StatefulWidget {
  const SourcingAgentPackingListDetailPage({
    required this.batchId,
    super.key,
    this.batchTitle,
  });

  final String batchId;
  final String? batchTitle;

  @override
  State<SourcingAgentPackingListDetailPage> createState() =>
      _SourcingAgentPackingListDetailPageState();
}

class _SourcingAgentPackingListDetailPageState
    extends State<SourcingAgentPackingListDetailPage> {
  final _repository = SourcingAgentBatchesRepository();
  late Future<List<Map<String, dynamic>>> _data = _load();

  Future<List<Map<String, dynamic>>> _load() => Future.wait([
    _repository.getBatch(widget.batchId),
    _repository.listOrders(widget.batchId),
  ]);

  void _retry() => setState(() => _data = _load());

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(
      role: 'Sourcing Agent',
      title: 'Packing list details',
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
            message: 'Packing-list details are unavailable right now.',
            actionLabel: 'Try again',
            onAction: _retry,
          );
        }

        final batch = snapshot.data![0];
        final orders = (snapshot.data![1]['orders'] as List? ?? const [])
            .cast<Map<String, dynamic>>();
        final cartons = orders.fold<int>(
          0,
          (sum, order) => sum + _asInt(order['carton_count']),
        );
        final totalWeight = orders.fold<double>(
          0,
          (sum, order) => sum + _readAmount(order['weight_kg']),
        );

        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              widget.batchTitle ?? batch['title'] as String? ?? 'Packing list',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 6),
            const Text(
              'Review totals, customer references, and export readiness for the batch shipment.',
            ),
            const SizedBox(height: 20),
            SahajomySectionCard(
              title: 'Document summary',
              children: [
                SahajomyKeyValueList(
                  entries: {
                    'shipping_method': batch['shipping_method'],
                    'orders': orders.length,
                    'cartons': cartons,
                    'weight_kg': totalWeight.toStringAsFixed(1),
                    'currency': batch['currency'],
                  },
                ),
              ],
            ),
            const SizedBox(height: 20),
            SahajomySectionCard(
              title: 'Item rows',
              children: [
                if (orders.isEmpty)
                  const Text(
                    'No order rows are available for this document yet.',
                  ),
                for (final order in orders)
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(order['order_reference'] as String? ?? 'Order'),
                    subtitle: Text(
                      order['customer_name'] as String? ?? 'Customer',
                    ),
                    trailing: Text(
                      '${_asInt(order['carton_count'])} cartons',
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 20),
            OutlinedButton.icon(
              onPressed: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text(
                      'Export actions can be connected when document endpoints are available.',
                    ),
                  ),
                );
              },
              icon: const Icon(Icons.download_outlined),
              label: const Text('Export packing list'),
            ),
          ],
        );
      },
    ),
  );
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
