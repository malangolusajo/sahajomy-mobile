import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../app/theme.dart';
import '../../../customer/presentation/customer_components.dart';
import '../../../repository_providers.dart';
import '../../batches/data/sourcing_agent_batches_repository.dart';

/// Screen 112 — Air cargo options
class AgentAirCargoOptionsPage extends ConsumerStatefulWidget {
  const AgentAirCargoOptionsPage({super.key});

  @override
  ConsumerState<AgentAirCargoOptionsPage> createState() => _AgentAirCargoOptionsPageState();
}

class _AgentAirCargoOptionsPageState extends ConsumerState<AgentAirCargoOptionsPage> {
  late Future<Map<String, dynamic>> _options;

  @override
  void initState() {
    super.initState();
    _options = ref.read(sourcingAgentBatchesRepositoryProvider).getAirCargoOptions();
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'AIR CARGO',
    title: 'Air cargo options',
    notificationRoute: '/reference/agent-notifications',
    body: FutureBuilder<Map<String, dynamic>>(
      future: _options,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return const CustomerEmptyState(icon: Icons.error_outline, message: 'Could not load air cargo options.');
        }
        final data = snapshot.data ?? {};
        final types = (data['cargo_types'] as List? ?? []).cast<Map<String, dynamic>>();
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          children: [
            CustomerHeroCard(
              eyebrow: data['service_name'] ?? 'Air Cargo',
              title: data['route'] ?? 'China → Africa',
              subtitle: '${data['delivery_window'] ?? ''} • Weight in ${data['allowed_weight_unit'] ?? 'KG'}',
            ),
            const SizedBox(height: 16),
            if (types.isEmpty)
              const CustomerEmptyState(icon: Icons.flight_outlined, message: 'No air cargo options available.')
            else
              for (final t in types) ...[
                Container(
                  margin: const EdgeInsets.only(bottom: 12),
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: appBorder)),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(children: [
                        Icon(t['is_hazardous'] == true ? Icons.warning_amber_rounded : Icons.inventory_2_outlined, color: t['is_hazardous'] == true ? appWarning : brandNavy),
                        const SizedBox(width: 8),
                        Expanded(child: Text(t['name'] ?? 'Goods type', style: const TextStyle(fontWeight: FontWeight.w800))),
                        if (t['requires_special_handling'] == true) CustomerStatusPill(label: 'special'),
                      ]),
                      const SizedBox(height: 8),
                      ...((t['rates'] as List? ?? []).cast<Map<String, dynamic>>()).map((r) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        child: Row(children: [
                          Expanded(child: Text(r['shipping_method'] ?? 'Standard', style: const TextStyle(fontSize: 13))),
                          Text('${r['price'] ?? '—'} ${r['currency'] ?? ''}/${r['unit'] ?? 'kg'}', style: const TextStyle(fontWeight: FontWeight.w700, color: brandCoral)),
                        ]),
                      )),
                    ],
                  ),
                ),
              ],
          ],
        );
      },
    ),
  );
}

/// Screen 113 — Book air cargo
class AgentBookAirCargoPage extends ConsumerStatefulWidget {
  const AgentBookAirCargoPage({super.key});

  @override
  ConsumerState<AgentBookAirCargoPage> createState() => _AgentBookAirCargoPageState();
}

class _AgentBookAirCargoPageState extends ConsumerState<AgentBookAirCargoPage> {
  final _formKey = GlobalKey<FormState>();
  final _weight = TextEditingController();
  final _region = TextEditingController();
  final _country = TextEditingController(text: 'Tanzania');
  final _cartons = TextEditingController(text: '1');
  final _desc = TextEditingController();
  String? _cargoTypeId;
  DateTime? _shipmentDate;
  bool _busy = false;
  late Future<Map<String, dynamic>> _options;

  @override
  void initState() {
    super.initState();
    _options = ref.read(sourcingAgentBatchesRepositoryProvider).getAirCargoOptions();
  }

  @override
  void dispose() {
    _weight.dispose(); _region.dispose(); _country.dispose(); _cartons.dispose(); _desc.dispose();
    super.dispose();
  }

  Future<void> _pickDate() async {
    final d = await showDatePicker(context: context, initialDate: DateTime.now().add(const Duration(days: 1)), firstDate: DateTime.now(), lastDate: DateTime.now().add(const Duration(days: 90)));
    if (d != null) setState(() => _shipmentDate = d);
  }

  Future<void> _book() async {
    if (!_formKey.currentState!.validate() || _cargoTypeId == null || _shipmentDate == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Please fill all fields and pick a date')));
      return;
    }
    setState(() => _busy = true);
    try {
      await ref.read(sourcingAgentBatchesRepositoryProvider).bookAirCargo(
        cargoTypeId: _cargoTypeId!,
        weightKg: double.parse(_weight.text),
        shipmentDate: _shipmentDate!,
        destinationRegion: _region.text.trim(),
        destinationCountry: _country.text.trim(),
        cartonCount: int.tryParse(_cartons.text) ?? 1,
        cargoDescription: _desc.text.trim().isEmpty ? null : _desc.text.trim(),
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Air cargo booked successfully')));
        Navigator.pop(context, true);
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'AIR CARGO',
    title: 'Book air cargo',
    notificationRoute: '/reference/agent-notifications',
    body: FutureBuilder<Map<String, dynamic>>(
      future: _options,
      builder: (context, snapshot) {
        final types = ((snapshot.data?['cargo_types'] as List?) ?? const []).cast<Map<String, dynamic>>();
        return Form(
          key: _formKey,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
            children: [
              const CustomerHeroCard(eyebrow: 'Express air', title: 'Book air cargo', subtitle: 'Send goods by air from China to Africa.'),
              const SizedBox(height: 16),
              DropdownButtonFormField<String>(
                value: _cargoTypeId,
                decoration: const InputDecoration(labelText: 'Cargo type'),
                items: types.map((t) => DropdownMenuItem(value: '${t['id']}', child: Text(t['name'] ?? ''))).toList(),
                onChanged: (v) => setState(() => _cargoTypeId = v),
                validator: (v) => v == null ? 'Select cargo type' : null,
              ),
              const SizedBox(height: 14),
              TextFormField(controller: _weight, decoration: const InputDecoration(labelText: 'Weight (KG)', suffixText: 'KG'), keyboardType: TextInputType.number, validator: (v) => double.tryParse(v ?? '') == null ? 'Enter weight' : null),
              const SizedBox(height: 14),
              InkWell(onTap: _pickDate, child: InputDecorator(decoration: const InputDecoration(labelText: 'Shipment date'), child: Text(_shipmentDate == null ? 'Select date' : _shipmentDate.toString().split(' ')[0], style: TextStyle(color: _shipmentDate == null ? appMuted : appInk)))),
              const SizedBox(height: 14),
              Row(children: [
                Expanded(child: TextFormField(controller: _region, decoration: const InputDecoration(labelText: 'Destination region'), validator: (v) => v!.isEmpty ? 'Required' : null)),
                const SizedBox(width: 12),
                Expanded(child: TextFormField(controller: _country, decoration: const InputDecoration(labelText: 'Country'))),
              ]),
              const SizedBox(height: 14),
              TextFormField(controller: _cartons, decoration: const InputDecoration(labelText: 'Carton count'), keyboardType: TextInputType.number),
              const SizedBox(height: 14),
              TextFormField(controller: _desc, decoration: const InputDecoration(labelText: 'Cargo description'), maxLines: 2),
              const SizedBox(height: 24),
              FilledButton.icon(onPressed: _busy ? null : _book, icon: const Icon(Icons.flight_takeoff_rounded), label: Text(_busy ? 'Booking...' : 'Confirm air booking')),
            ],
          ),
        );
      },
    ),
  );
}

/// Screen 114 — Air shipping label
class AgentAirShippingLabelPage extends ConsumerStatefulWidget {
  const AgentAirShippingLabelPage({required this.bookingId, super.key});
  final String bookingId;

  @override
  ConsumerState<AgentAirShippingLabelPage> createState() => _AgentAirShippingLabelPageState();
}

class _AgentAirShippingLabelPageState extends ConsumerState<AgentAirShippingLabelPage> {
  late Future<Map<String, dynamic>> _label;

  @override
  void initState() {
    super.initState();
    _label = ref.read(sourcingAgentBatchesRepositoryProvider).getAirShippingLabel(widget.bookingId);
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'AIR CARGO',
    title: 'Shipping label',
    notificationRoute: '/reference/agent-notifications',
    body: FutureBuilder<Map<String, dynamic>>(
      future: _label,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return const CustomerEmptyState(icon: Icons.error_outline, message: 'Could not load shipping label.');
        }
        final l = snapshot.data ?? {};
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Center(child: Icon(Icons.local_shipping_rounded, size: 48, color: brandNavy)),
                  const SizedBox(height: 8),
                  Center(child: Text(l['label_number'] ?? 'LABEL', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 18))),
                  const Divider(height: 24),
                  _labelRow('Tracking', l['tracking_number'] ?? '—'),
                  _labelRow('Route', l['route'] ?? '—'),
                  _labelRow('Weight', '${l['weight_kg'] ?? '—'} KG'),
                  _labelRow('Cartons', '${l['carton_count'] ?? '—'}'),
                  _labelRow('Destination', l['destination_region'] ?? '—'),
                  if (l['status'] != null) _labelRow('Status', l['status']),
                ],
              ),
            ),
          ],
        );
      },
    ),
  );

  Widget _labelRow(String k, String v) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 6),
    child: Row(children: [
      SizedBox(width: 110, child: Text(k, style: const TextStyle(color: appMuted, fontSize: 13))),
      Expanded(child: Text(v, style: const TextStyle(fontWeight: FontWeight.w700))),
    ]),
  );
}

/// Screen 179 — Edit shipping label
class AgentEditShippingLabelPage extends ConsumerStatefulWidget {
  const AgentEditShippingLabelPage({required this.bookingId, required this.label, super.key});
  final String bookingId;
  final Map<String, dynamic> label;

  @override
  ConsumerState<AgentEditShippingLabelPage> createState() => _AgentEditShippingLabelPageState();
}

class _AgentEditShippingLabelPageState extends ConsumerState<AgentEditShippingLabelPage> {
  final _tracking = TextEditingController();
  final _region = TextEditingController();
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _tracking.text = '${widget.label['tracking_number'] ?? ''}';
    _region.text = '${widget.label['destination_region'] ?? ''}';
  }

  @override
  void dispose() {
    _tracking.dispose(); _region.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() => _busy = true);
    try {
      await ref.read(sourcingAgentBatchesRepositoryProvider).updateAirShippingLabel(widget.bookingId, {
        if (_tracking.text.trim().isNotEmpty) 'tracking_number': _tracking.text.trim(),
        if (_region.text.trim().isNotEmpty) 'destination_region': _region.text.trim(),
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Label updated')));
        Navigator.pop(context, true);
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'AIR CARGO',
    title: 'Edit shipping label',
    notificationRoute: '/reference/agent-notifications',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        const CustomerHeroCard(eyebrow: 'Label', title: 'Edit shipping label', subtitle: 'Update tracking and destination details.'),
        const SizedBox(height: 16),
        TextFormField(controller: _tracking, decoration: const InputDecoration(labelText: 'Tracking number')),
        const SizedBox(height: 14),
        TextFormField(controller: _region, decoration: const InputDecoration(labelText: 'Destination region')),
        const SizedBox(height: 24),
        FilledButton(onPressed: _busy ? null : _save, child: Text(_busy ? 'Saving...' : 'Save changes')),
      ],
    ),
  );
}
