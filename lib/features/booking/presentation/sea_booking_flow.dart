import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/ui/logistics_ui.dart';
import '../../../core/ui/sahajomy_ui.dart';
import '../../customer/presentation/customer_components.dart';
import '../../repository_providers.dart';
import '../data/guided_booking_repository.dart';

class GuidedSeaBookingPage extends ConsumerStatefulWidget {
  const GuidedSeaBookingPage({required this.account, this.initialContainerId, super.key});
  final BookingAccount account;
  final String? initialContainerId;
  @override
  ConsumerState<GuidedSeaBookingPage> createState() => _SeaBookingState();
}

class _SeaBookingState extends ConsumerState<GuidedSeaBookingPage> {
  final _form = GlobalKey<FormState>();
  final _volume = TextEditingController();
  final _city = TextEditingController();
  final _country = TextEditingController();
  final _cartons = TextEditingController();
  List<Map<String, dynamic>> _services = [];
  Map<String, dynamic>? _selected;
  Map<String, dynamic>? _address;
  Map<String, dynamic>? _booking;
  String _search = '';
  String? _error;
  int _step = 0;
  int _limit = 3;
  bool _busy = false;
  bool _loading = true;
  bool get _customer => widget.account == BookingAccount.customer;
  GuidedBookingRepository get _repo => ref.read(guidedBookingRepositoryProvider);
  String _route(Map<String, dynamic> s) => '${s['route'] ?? '${s['origin'] ?? 'Origin pending'} → ${s['destination'] ?? 'Destination pending'}'}';
  bool _available(Map<String, dynamic> s) => const ['open', 'nearly_full'].contains(s['status']) && (num.tryParse('${s['available_cbm']}') ?? 0) > 0;

  @override
  void initState() { super.initState(); _load(); }
  @override
  void dispose() { _volume.dispose(); _city.dispose(); _country.dispose(); _cartons.dispose(); super.dispose(); }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final services = await _repo.listSeaServices(account: widget.account);
      if (!mounted) return;
      setState(() { _services = services; _loading = false; });
      if (widget.initialContainerId != null) {
        final selected = services.where((s) => '${s['id']}' == widget.initialContainerId);
        if (selected.isNotEmpty && _available(selected.first)) {
          _choose(selected.first);
        } else { setState(() => _error = 'This container is no longer available. Choose another sailing.'); }
      }
    } catch (error) {
      if (mounted) setState(() { _error = logisticsError(error, 'sea freight services'); _loading = false; });
    }
  }

  void _choose(Map<String, dynamic> service) {
    setState(() {
      _selected = service; _address = null; _error = null; _step = 1;
      _city.text = service['destination']?.toString() ?? '';
      _country.text = service['destination_country']?.toString() ?? '';
    });
  }

  Future<void> _review() async {
    if (_busy || !_form.currentState!.validate()) return;
    setState(() { _busy = true; _error = null; _address = null; });
    try {
      final address = await _repo.prepareSeaAddress(containerId: '${_selected!['id']}', destinationCity: _city.text.trim(), destinationCountry: _country.text.trim());
      if (mounted) setState(() { _address = address; _step = 2; });
    } catch (error) {
      if (mounted) setState(() => _error = logisticsError(error, 'China forwarding address'));
    } finally { if (mounted) setState(() => _busy = false); }
  }

  Future<void> _confirm() async {
    if (_busy || _selected == null || _address == null) return;
    setState(() { _busy = true; _error = null; });
    try {
      final volume = double.parse(_volume.text.trim());
      final booking = await _repo.confirmSeaBooking(account: widget.account, payload: {
        'container_id': '${_selected!['id']}',
        if (_customer) 'booked_cbm': volume else 'cbm_amount': volume,
        if (_customer) 'destination_region': _city.text.trim() else 'destination_city': _city.text.trim(),
        'destination_country': _country.text.trim(),
        if (_customer && _cartons.text.trim().isNotEmpty) 'carton_count': int.parse(_cartons.text.trim()),
      });
      if (mounted) setState(() { _booking = booking; _step = 3; });
    } catch (error) {
      if (mounted) setState(() => _error = logisticsError(error, 'cargo booking'));
    } finally { if (mounted) setState(() => _busy = false); }
  }

  String? _required(String? value) => value == null || value.trim().length < 2 ? 'Enter at least two characters.' : null;

  @override
  Widget build(BuildContext context) {
    final body = ListView(padding: const EdgeInsets.fromLTRB(24, 12, 24, 32), children: [
      Row(children: [for (var i = 0; i < 3; i++) Expanded(child: Semantics(
        label: '${const ['Service', 'Cargo details', 'Review'][i]}, ${i < _step ? 'complete' : i == _step ? 'current' : 'upcoming'}',
        child: Column(children: [
          Icon(i < _step ? Icons.check_circle : i == _step ? Icons.radio_button_checked : Icons.radio_button_unchecked, color: i <= _step ? Theme.of(context).colorScheme.primary : Colors.grey),
          const SizedBox(height: 6), Text(const ['Service', 'Cargo', 'Review'][i]),
        ]),
      ))]),
      const SizedBox(height: 28),
      if (_error != null) ...[Semantics(liveRegion: true, child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error))), const SizedBox(height: 16)],
      if (_step == 0) ..._servicesView() else if (_step == 1) _details() else if (_step == 2) ..._reviewView() else ..._confirmationView(),
    ]);
    return _customer
        ? CustomerScaffold(title: 'Book sea freight', body: body)
        : Scaffold(
            appBar: SahajomyScreenHeader(role: 'Sourcing Agent', title: 'Book sea freight'),
            body: body,
          );
  }

  List<Widget> _servicesView() {
    final matches = _services.where((s) => '${_route(s)} ${s['operator']} ${s['container_size']}'.toLowerCase().contains(_search.toLowerCase())).toList();
    return [
      const LogisticsIntro(eyebrow: 'Sea freight', title: 'Choose your sailing', description: 'Compare cargo companies, available space and published rates.'),
      TextField(onChanged: (value) => setState(() { _search = value; _limit = 20; }), decoration: const InputDecoration(labelText: 'Search origin, destination or company', prefixIcon: Icon(Icons.search))),
      const SizedBox(height: 20),
      if (_loading) const Center(child: CircularProgressIndicator())
      else if (_error != null && _services.isEmpty) OutlinedButton(onPressed: _load, child: const Text('Reload sea services'))
      else if (matches.isEmpty) const SahajomyMessageState(icon: Icons.directions_boat_outlined, message: 'No sailings match your search.'),
      for (final service in matches.take(_limit)) Padding(padding: const EdgeInsets.only(bottom: 12), child: Card(child: Padding(
        padding: const EdgeInsets.all(18), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${service['operator'] ?? service['operator_name'] ?? 'Cargo company'}', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 6), Text(_route(service), style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          Wrap(spacing: 12, runSpacing: 8, children: [Text('${service['available_cbm'] ?? '—'} CBM available'), SahajomyStatusPill(label: '${service['status'] ?? 'Status unavailable'}')]),
          const SizedBox(height: 8), Text('${service['price_per_cbm'] ?? 'Rate pending'} ${service['currency'] ?? ''} / CBM'),
          const SizedBox(height: 14),
          SizedBox(width: double.infinity, child: OutlinedButton(onPressed: _available(service) ? () => _choose(service) : null, child: Text(_available(service) ? 'Choose this sailing' : 'Booking unavailable'))),
        ]),
      ))),
      if (matches.length > _limit) TextButton(onPressed: () => setState(() => _limit += 20), child: Text(_limit == 3 ? 'Browse all sailings' : 'Show more sailings')),
    ];
  }

  Widget _details() => AbsorbPointer(absorbing: _busy, child: Form(key: _form, child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
    LogisticsIntro(eyebrow: '${_selected!['operator'] ?? 'Selected sailing'}', title: 'Cargo details', description: _route(_selected!)),
    TextFormField(controller: _volume, keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: const InputDecoration(labelText: 'Cargo volume (CBM)'), validator: (text) {
      final value = double.tryParse(text?.trim() ?? '');
      if (value == null || !value.isFinite || value <= 0) return 'Enter a volume greater than zero.';
      final max = num.tryParse('${_selected!['available_cbm']}');
      if (max != null && value > max) return 'Only $max CBM is currently available.';
      if (!_customer && value > 100000) return 'Volume must not exceed 100,000 CBM.';
      return null;
    }),
    const SizedBox(height: 16),
    TextFormField(controller: _city, maxLength: 120, decoration: const InputDecoration(labelText: 'Destination city'), validator: _required),
    const SizedBox(height: 8),
    TextFormField(controller: _country, maxLength: 100, decoration: const InputDecoration(labelText: 'Destination country'), validator: _required),
    if (_customer) ...[const SizedBox(height: 8), TextFormField(controller: _cartons, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Carton count (optional)'), validator: (value) {
      if (value == null || value.trim().isEmpty) return null;
      return (int.tryParse(value.trim()) ?? 0) > 0 ? null : 'Enter a positive whole number.';
    })],
    const SizedBox(height: 24),
    FilledButton(onPressed: _busy ? null : _review, child: Text(_busy ? 'Preparing China address…' : 'Review cargo booking')),
    TextButton(onPressed: _busy ? null : () => setState(() { _step = 0; _address = null; }), child: const Text('Change sailing')),
  ])));

  List<Widget> _reviewView() => [
    const LogisticsIntro(title: 'Review your booking', description: 'Check your cargo and destination before confirming the booking.'),
    SahajomyKeyValueList(entries: {
      'Cargo company': _selected!['operator'] ?? _selected!['operator_name'], 'Route': _route(_selected!), 'Cargo volume': '${_volume.text} CBM',
      'Destination': '${_city.text}, ${_country.text}', if (_customer && _cartons.text.isNotEmpty) 'Cartons': _cartons.text,
      'Published rate per CBM': '${_selected!['price_per_cbm'] ?? 'Pending'} ${_selected!['currency'] ?? ''}',
    }),
    const SizedBox(height: 24), const Text('Supplier shipping mark', style: TextStyle(fontWeight: FontWeight.w800)), const SizedBox(height: 8),
    SelectableText('${(_address!['copy'] as Map?)?['shipping_mark'] ?? _address!['shipping_mark'] ?? 'Not provided'}'),
    TextButton(onPressed: () => context.push(_customer ? '/customer/china-addresses' : '/agent/china-addresses'), child: const Text('View China warehouse address')),
    const SizedBox(height: 20),
    FilledButton(onPressed: _busy ? null : _confirm, child: Text(_busy ? 'Confirming booking…' : 'Confirm cargo booking')),
    TextButton(onPressed: _busy ? null : () => setState(() { _step = 1; _address = null; }), child: const Text('Edit cargo details')),
  ];

  List<Widget> _confirmationView() => [
    const Icon(Icons.check_circle_outline_rounded, size: 64, color: Color(0xFF08705F)), const SizedBox(height: 20),
    const LogisticsIntro(title: 'Cargo space booked', description: 'Your sea freight booking has been created. Payment and cargo status are shown below.'),
    SahajomyKeyValueList(entries: {
      'Booking reference': _booking!['booking_reference'] ?? _booking!['sea_booking_id'] ?? _booking!['id'], 'Tracking number': _booking!['tracking_number'],
      'Booked volume': '${_booking!['cbm_booked'] ?? _volume.text} CBM', 'Freight charge': '${_booking!['logistics_charge'] ?? 'Pending'} ${_booking!['currency'] ?? ''}',
      'Payment status': _booking!['payment_status'], if (_booking!['goods_status'] != null) 'Cargo status': _booking!['goods_status'],
    }),
    const SizedBox(height: 24),
    FilledButton(onPressed: () => context.go(_customer ? '/customer/sea-bookings' : '/agent/sea-bookings'), child: const Text('View cargo bookings')),
    TextButton(onPressed: () { _volume.clear(); _cartons.clear(); setState(() { _booking = null; _selected = null; _address = null; _step = 0; }); _load(); }, child: const Text('Book another sailing')),
  ];
}
