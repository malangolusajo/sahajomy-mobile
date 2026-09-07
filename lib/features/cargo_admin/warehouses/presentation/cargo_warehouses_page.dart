import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../../../features/repository_providers.dart';
import '../../../customer/presentation/customer_components.dart';

class CargoWarehousesPage extends ConsumerStatefulWidget {
  const CargoWarehousesPage({super.key});

  @override
  ConsumerState<CargoWarehousesPage> createState() => _CargoWarehousesPageState();
}

class _CargoWarehousesPageState extends ConsumerState<CargoWarehousesPage> {
  late Future<List<Map<String, dynamic>>> _warehouses;

  @override
  void initState() {
    super.initState();
    _warehouses = ref.read(cargoOperationsRepositoryProvider).listWarehouses();
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'CARGO COMPANY',
    title: 'Warehouses',
    notificationRoute: '/cargo/notifications',
    floatingActionButton: FloatingActionButton.extended(
      onPressed: () => context.push('/cargo/warehouses/new'),
      icon: const Icon(Icons.add),
      label: const Text('Add warehouse'),
    ),
    body: RefreshIndicator(
      onRefresh: () async {
        setState(() {
          _warehouses = ref.read(cargoOperationsRepositoryProvider).listWarehouses();
        });
        await _warehouses;
      },
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 100),
        children: [
          const CustomerHeroCard(
            eyebrow: 'Warehouses',
            title: 'Your warehouse locations',
            subtitle: 'Manage origins, destinations, and China forwarding addresses.',
          ),
          const SizedBox(height: 20),
          FutureBuilder<List<Map<String, dynamic>>>(
            future: _warehouses,
            builder: (context, snapshot) {
              if (snapshot.connectionState != ConnectionState.done) return const CustomerSkeletonList(count: 4);
              if (snapshot.hasError) {
                return CustomerEmptyState(
                  icon: Icons.error_outline,
                  message: 'Could not load warehouses.',
                  actionLabel: 'Retry',
                  onAction: () => setState(() {
                    _warehouses = ref.read(cargoOperationsRepositoryProvider).listWarehouses();
                  }),
                );
              }
              final list = snapshot.data ?? [];
              if (list.isEmpty) return const CustomerEmptyState(icon: Icons.warehouse_outlined, message: 'No warehouses yet.');
              return Column(children: [for (final w in list) _warehouseCard(w)]);
            },
          ),
        ],
      ),
    ),
  );

  Widget _warehouseCard(Map<String, dynamic> w) => GestureDetector(
    onTap: () => context.push('/cargo/warehouses/${w['id']}'),
    child: Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)),
      child: Row(
        children: [
          Container(width: 44, height: 44, alignment: Alignment.center, decoration: BoxDecoration(color: brandCoral.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(12)), child: const Icon(Icons.warehouse, color: brandCoral)),
          const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(w['name'] ?? 'Warehouse', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
            const SizedBox(height: 2),
            Text([w['city'], w['country']].whereType<String>().where((s) => s.isNotEmpty).join(', '), style: const TextStyle(color: appMuted, fontSize: 13)),
          ])),
          const Icon(Icons.chevron_right, color: appMuted),
        ],
      ),
    ),
  );
}

class CargoWarehouseDetailPage extends ConsumerStatefulWidget {
  const CargoWarehouseDetailPage({required this.warehouseId, super.key});
  final String warehouseId;

  @override
  ConsumerState<CargoWarehouseDetailPage> createState() => _CargoWarehouseDetailPageState();
}

class _CargoWarehouseDetailPageState extends ConsumerState<CargoWarehouseDetailPage> {
  late Future<Map<String, dynamic>> _warehouse;

  @override
  void initState() {
    super.initState();
    _warehouse = ref.read(cargoOperationsRepositoryProvider).getWarehouse(widget.warehouseId);
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'WAREHOUSE',
    title: 'Warehouse detail',
    notificationRoute: '/cargo/notifications',
    body: FutureBuilder<Map<String, dynamic>>(
      future: _warehouse,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
        if (snapshot.hasError) return const CustomerEmptyState(icon: Icons.error_outline, message: 'Could not load warehouse.');
        final w = snapshot.data ?? {};
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          children: [
            CustomerHeroCard(eyebrow: w['warehouse_type'] ?? 'warehouse', title: w['name'] ?? 'Warehouse', subtitle: '${w['address'] ?? ''}, ${w['city'] ?? ''}, ${w['country'] ?? ''}'),
            const SizedBox(height: 20),
            _panel([
              _row('CT', 'City', w['city'] ?? '—', appMuted),
              const Divider(height: 1, indent: 60),
              _row('AD', 'Address', w['address'] ?? '—', appMuted),
              const Divider(height: 1, indent: 60),
              _row('PH', 'Phone', w['contact_phone_1'] ?? '—', appMuted),
              const Divider(height: 1, indent: 60),
              _row('CN', 'China address', (w['china_address_status'] ?? 'not configured').toString().replaceAll('_', ' '), brandCoral),
            ]),
            const SizedBox(height: 24),
            FilledButton.icon(onPressed: () => context.push('/cargo/warehouses/${widget.warehouseId}/qr'), icon: const Icon(Icons.qr_code), label: const Text('Warehouse QR code')),
            const SizedBox(height: 12),
            OutlinedButton.icon(onPressed: () => context.push('/cargo/warehouses/${widget.warehouseId}/china-address'), icon: const Icon(Icons.edit_location), label: const Text('Edit China address')),
          ],
        );
      },
    ),
  );

  Widget _panel(List<Widget> children) => Container(decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)), child: Column(children: children));

  Widget _row(String badge, String title, String subtitle, Color badgeColor) => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    child: Row(children: [
      Container(width: 40, height: 40, alignment: Alignment.center, decoration: BoxDecoration(color: badgeColor.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(10)), child: Text(badge, style: TextStyle(color: badgeColor, fontWeight: FontWeight.w800))),
      const SizedBox(width: 14),
      Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
        const SizedBox(height: 2),
        Text(subtitle, style: const TextStyle(color: appMuted, fontSize: 13)),
      ])),
    ]),
  );
}

class CargoAddWarehousePage extends ConsumerStatefulWidget {
  const CargoAddWarehousePage({super.key});

  @override
  ConsumerState<CargoAddWarehousePage> createState() => _CargoAddWarehousePageState();
}

class _CargoAddWarehousePageState extends ConsumerState<CargoAddWarehousePage> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _country = TextEditingController(text: 'China');
  final _city = TextEditingController();
  final _address = TextEditingController();
  final _phone = TextEditingController();
  String _type = 'both';
  bool _busy = false;

  @override
  void dispose() {
    _name.dispose();
    _country.dispose();
    _city.dispose();
    _address.dispose();
    _phone.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      await ref.read(cargoOperationsRepositoryProvider).createWarehouse({
        'name': _name.text.trim(),
        'country': _country.text.trim(),
        'city': _city.text.trim(),
        'address': _address.text.trim(),
        'contact_phone_1': _phone.text.trim(),
        'warehouse_type': _type,
      });
      if (mounted) context.go('/cargo/warehouses');
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'WAREHOUSE',
    title: 'Add warehouse',
    notificationRoute: '/cargo/notifications',
    body: Form(
      key: _formKey,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          TextFormField(controller: _name, decoration: const InputDecoration(labelText: 'Warehouse name'), validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null),
          const SizedBox(height: 16),
          TextFormField(controller: _country, decoration: const InputDecoration(labelText: 'Country'), validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null),
          const SizedBox(height: 16),
          TextFormField(controller: _city, decoration: const InputDecoration(labelText: 'City')),
          const SizedBox(height: 16),
          TextFormField(controller: _address, decoration: const InputDecoration(labelText: 'Address')),
          const SizedBox(height: 16),
          TextFormField(controller: _phone, decoration: const InputDecoration(labelText: 'Contact phone'), keyboardType: TextInputType.phone),
          const SizedBox(height: 16),
          DropdownButtonFormField<String>(
            value: _type,
            decoration: const InputDecoration(labelText: 'Warehouse type'),
            items: const [
              DropdownMenuItem(value: 'sea', child: Text('Sea')),
              DropdownMenuItem(value: 'air', child: Text('Air')),
              DropdownMenuItem(value: 'both', child: Text('Both')),
            ],
            onChanged: (v) => setState(() => _type = v ?? 'both'),
          ),
          const SizedBox(height: 24),
          FilledButton(onPressed: _busy ? null : _submit, child: Text(_busy ? 'Creating...' : 'Create warehouse')),
        ],
      ),
    ),
  );
}

class CargoChinaAddressPage extends ConsumerStatefulWidget {
  const CargoChinaAddressPage({required this.warehouseId, super.key});
  final String warehouseId;

  @override
  ConsumerState<CargoChinaAddressPage> createState() => _CargoChinaAddressPageState();
}

class _CargoChinaAddressPageState extends ConsumerState<CargoChinaAddressPage> {
  final _formKey = GlobalKey<FormState>();
  late Future<Map<String, dynamic>> _warehouse;
  bool _loaded = false;
  bool _busy = false;

  final _nameZh = TextEditingController();
  final _receiver = TextEditingController();
  final _mobile = TextEditingController();
  final _province = TextEditingController();
  final _city = TextEditingController();
  final _district = TextEditingController();
  final _street = TextEditingController();
  final _detailed = TextEditingController();
  final _original = TextEditingController();

  @override
  void initState() {
    super.initState();
    _warehouse = ref.read(cargoOperationsRepositoryProvider).getWarehouse(widget.warehouseId);
    _warehouse.then((w) {
      if (!mounted) return;
      _nameZh.text = w['name_zh'] ?? '';
      _receiver.text = w['china_receiver_name'] ?? '';
      _mobile.text = w['china_mobile'] ?? '';
      _province.text = w['china_province'] ?? '';
      _city.text = w['china_city'] ?? '';
      _district.text = w['china_district'] ?? '';
      _street.text = w['china_street'] ?? '';
      _detailed.text = w['china_detailed_address'] ?? '';
      _original.text = w['china_original_address'] ?? '';
      setState(() => _loaded = true);
    });
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      await ref.read(cargoOperationsRepositoryProvider).updateWarehouse(widget.warehouseId, {
        'name_zh': _nameZh.text.trim(),
        'china_receiver_name': _receiver.text.trim(),
        'china_mobile': _mobile.text.trim(),
        'china_province': _province.text.trim(),
        'china_city': _city.text.trim(),
        'china_district': _district.text.trim(),
        'china_street': _street.text.trim(),
        'china_detailed_address': _detailed.text.trim(),
        'china_original_address': _original.text.trim(),
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('China address saved')));
        context.pop();
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'WAREHOUSE',
    title: 'China address structure',
    notificationRoute: '/cargo/notifications',
    body: FutureBuilder<Map<String, dynamic>>(
      future: _warehouse,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return const CustomerEmptyState(icon: Icons.error_outline, message: 'Could not load warehouse.');
        }
        final w = snapshot.data ?? {};
        final status = (w['china_address_status'] ?? 'not_configured').toString();
        return Form(
          key: _formKey,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
            children: [
              CustomerHeroCard(
                eyebrow: w['name'] ?? 'Warehouse',
                title: 'China forwarding address',
                subtitle: 'Receiver name, mobile, and structured address for marketplace dropship.',
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                decoration: BoxDecoration(
                  color: (status == 'ready' ? appSuccess : brandCoral).withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: status == 'ready' ? appSuccess : brandCoral),
                ),
                child: Row(children: [
                  Icon(status == 'ready' ? Icons.check_circle : Icons.info_outline, color: status == 'ready' ? appSuccess : brandCoral),
                  const SizedBox(width: 10),
                  Text('Status: ${status.replaceAll('_', ' ')}', style: TextStyle(color: status == 'ready' ? appSuccess : brandCoral, fontWeight: FontWeight.w700)),
                ]),
              ),
              const SizedBox(height: 20),
              _field('Warehouse name (Chinese)', _nameZh),
              const SizedBox(height: 14),
              _field('Receiver name', _receiver),
              const SizedBox(height: 14),
              _field('Mobile phone', _mobile, keyboardType: TextInputType.phone),
              const SizedBox(height: 14),
              Row(children: [
                Expanded(child: _field('Province', _province)),
                const SizedBox(width: 12),
                Expanded(child: _field('City', _city)),
              ]),
              const SizedBox(height: 14),
              _field('District / County', _district),
              const SizedBox(height: 14),
              _field('Street', _street),
              const SizedBox(height: 14),
              TextFormField(
                controller: _detailed,
                decoration: const InputDecoration(labelText: 'Detailed address'),
                maxLines: 3,
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: _original,
                decoration: const InputDecoration(labelText: 'Original address (raw text)'),
                maxLines: 2,
              ),
              const SizedBox(height: 24),
              FilledButton.icon(
                onPressed: _busy ? null : _save,
                icon: const Icon(Icons.save),
                label: Text(_busy ? 'Saving...' : 'Save address'),
              ),
            ],
          ),
        );
      },
    ),
  );

  Widget _field(String label, TextEditingController controller, {TextInputType? keyboardType}) => TextFormField(
    controller: controller,
    keyboardType: keyboardType,
    decoration: InputDecoration(labelText: label),
  );
}
