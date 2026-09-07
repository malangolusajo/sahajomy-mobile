import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../../../features/repository_providers.dart';
import '../../../customer/presentation/customer_components.dart';

class CargoContainerDetailPage extends ConsumerStatefulWidget {
  const CargoContainerDetailPage({required this.containerId, super.key});
  final String containerId;

  @override
  ConsumerState<CargoContainerDetailPage> createState() => _CargoContainerDetailPageState();
}

class _CargoContainerDetailPageState extends ConsumerState<CargoContainerDetailPage> {
  late Future<Map<String, dynamic>> _container;
  late Future<List<Map<String, dynamic>>> _reservations;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _container = ref.read(cargoOperationsRepositoryProvider).listContainers().then(
      (list) => list.firstWhere((c) => c['id'] == widget.containerId, orElse: () => {}),
    );
    _reservations = ref.read(cargoOperationsRepositoryProvider).containerReservations(widget.containerId);
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'CONTAINER',
    title: 'Container detail',
    notificationRoute: '/cargo/notifications',
    body: FutureBuilder<Map<String, dynamic>>(
      future: _container,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
        final c = snapshot.data ?? {};
        if (c.isEmpty) return const CustomerEmptyState(icon: Icons.error_outline, message: 'Container not found.');
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          children: [
            CustomerHeroCard(
              eyebrow: c['container_size'] ?? 'container',
              title: c['reference'] ?? 'Container',
              subtitle: '${c['warehouse_origin_name'] ?? 'Origin'} → ${c['warehouse_destination_name'] ?? 'Destination'}',
            ),
            const SizedBox(height: 16),
            Row(children: [
              Expanded(child: _metric('Max CBM', '${c['max_cbm'] ?? 0}')),
              const SizedBox(width: 12),
              Expanded(child: _metric('Booked', '${c['reserved_cbm'] ?? 0}')),
              const SizedBox(width: 12),
              Expanded(child: _metric('Price/CBM', '${c['price_per_cbm'] ?? 0}')),
            ]),
            const SizedBox(height: 20),
            _panel([
              _row('ST', 'Status', (c['status'] ?? 'draft').toString().replaceAll('_', ' '), brandCoral),
              const Divider(height: 1, indent: 60),
              _row('DP', 'Departure', (c['departure_date'] ?? 'TBD').toString().substring(0, 10), appMuted),
              const Divider(height: 1, indent: 60),
              _row('AR', 'ETA', (c['estimated_arrival_date'] ?? 'TBD').toString().substring(0, 10), appMuted),
            ]),
            const SizedBox(height: 24),
            Row(children: [
              Expanded(child: FilledButton.icon(onPressed: () => _updateStatus('open'), icon: const Icon(Icons.play_arrow), label: const Text('Open'))),
              const SizedBox(width: 10),
              Expanded(child: OutlinedButton.icon(onPressed: () => _updateStatus('in_transit'), icon: const Icon(Icons.flight), label: const Text('Depart'))),
            ]),
            const SizedBox(height: 12),
            FilledButton.icon(onPressed: () => context.push('/cargo/containers/${widget.containerId}/consolidated-packing-list'), icon: const Icon(Icons.list_alt), label: const Text('Consolidated packing list')),
            const SizedBox(height: 20),
            const CustomerSectionHeader(title: 'Bookings'),
            const SizedBox(height: 8),
            FutureBuilder<List<Map<String, dynamic>>>(
              future: _reservations,
              builder: (context, snap) {
                final list = snap.data ?? [];
                if (list.isEmpty) return const CustomerEmptyState(icon: Icons.inbox_outlined, message: 'No bookings yet.');
                return Container(decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)), child: Column(children: [
                  for (var i = 0; i < list.length; i++) ...[
                    _resRow(list[i]),
                    if (i < list.length - 1) const Divider(height: 1, indent: 60),
                  ],
                ]));
              },
            ),
          ],
        );
      },
    ),
  );

  Widget _metric(String label, String value) => Container(padding: const EdgeInsets.all(12), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12), border: Border.all(color: appBorder)), child: Column(children: [
    Text(label, style: const TextStyle(color: appMuted, fontSize: 11)),
    const SizedBox(height: 4),
    Text(value, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
  ]));

  Widget _panel(List<Widget> children) => Container(decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)), child: Column(children: children));

  Widget _row(String badge, String title, String subtitle, Color badgeColor) => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    child: Row(children: [
      Container(width: 40, height: 40, alignment: Alignment.center, decoration: BoxDecoration(color: badgeColor.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(10)), child: Text(badge, style: TextStyle(color: badgeColor, fontWeight: FontWeight.w800))),
      const SizedBox(width: 14),
      Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)), const SizedBox(height: 2), Text(subtitle, style: const TextStyle(color: appMuted, fontSize: 13))])),
    ]),
  );

  Widget _resRow(Map<String, dynamic> r) => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    child: Row(children: [
      Container(width: 40, height: 40, alignment: Alignment.center, decoration: BoxDecoration(color: brandCoral.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(10)), child: const Text('RS', style: TextStyle(color: brandCoral, fontWeight: FontWeight.w800))),
      const SizedBox(width: 14),
      Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(r['shipping_mark'] ?? r['id'] ?? 'Booking', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
        const SizedBox(height: 2),
        Text('${r['cbm_reserved'] ?? 0} CBM · ${r['goods_status'] ?? 'pending'}', style: const TextStyle(color: appMuted, fontSize: 13)),
      ])),
      CustomerStatusPill(label: (r['goods_status'] ?? 'pending').toString().replaceAll('_', ' ')),
    ]),
  );

  Future<void> _updateStatus(String status) async {
    try {
      await ref.read(cargoOperationsRepositoryProvider).updateContainerStatus(widget.containerId, status: status);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Status updated')));
        setState(_reload);
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    }
  }
}

class CargoCreateContainerPage extends ConsumerStatefulWidget {
  const CargoCreateContainerPage({super.key});

  @override
  ConsumerState<CargoCreateContainerPage> createState() => _CargoCreateContainerPageState();
}

class _CargoCreateContainerPageState extends ConsumerState<CargoCreateContainerPage> {
  final _formKey = GlobalKey<FormState>();
  final _size = TextEditingController(text: '40ft');
  final _maxCbm = TextEditingController(text: '68');
  final _price = TextEditingController(text: '35000');
  String _originWarehouse = '';
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _loadWarehouses();
  }

  List<Map<String, dynamic>> _warehouses = [];

  Future<void> _loadWarehouses() async {
    final list = await ref.read(cargoOperationsRepositoryProvider).listWarehouses();
    setState(() {
      _warehouses = list;
      if (list.isNotEmpty) _originWarehouse = list.first['id'];
    });
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'CONTAINER',
    title: 'Create container',
    notificationRoute: '/cargo/notifications',
    body: Form(
      key: _formKey,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          TextFormField(controller: _size, decoration: const InputDecoration(labelText: 'Container size (20ft / 40ft)'), validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null),
          const SizedBox(height: 16),
          DropdownButtonFormField<String>(
            value: _originWarehouse.isEmpty ? null : _originWarehouse,
            decoration: const InputDecoration(labelText: 'Origin warehouse'),
            items: _warehouses.map((w) => DropdownMenuItem<String>(value: w['id'].toString(), child: Text(w['name'] ?? 'Warehouse'))).toList(),
            onChanged: (v) => setState(() => _originWarehouse = v ?? ''),
            validator: (v) => (v == null || v.isEmpty) ? 'Select a warehouse' : null,
          ),
          const SizedBox(height: 16),
          TextFormField(controller: _maxCbm, decoration: const InputDecoration(labelText: 'Max CBM'), keyboardType: TextInputType.number, validator: (v) => (v == null || double.tryParse(v) == null) ? 'Required' : null),
          const SizedBox(height: 16),
          TextFormField(controller: _price, decoration: const InputDecoration(labelText: 'Price per CBM (TZS)'), keyboardType: TextInputType.number),
          const SizedBox(height: 24),
          FilledButton(onPressed: _busy ? null : _submit, child: Text(_busy ? 'Creating...' : 'Create container')),
        ],
      ),
    ),
  );

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      await ref.read(cargoOperationsRepositoryProvider).createContainer({
        'container_size': _size.text.trim(),
        'warehouse_origin_id': _originWarehouse,
        'max_cbm': double.parse(_maxCbm.text),
        'price_per_cbm': double.parse(_price.text),
        'currency': 'TZS',
        'status': 'open',
      });
      if (mounted) context.go('/cargo/containers');
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }
}
