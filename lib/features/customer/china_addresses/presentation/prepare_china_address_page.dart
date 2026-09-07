import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../features/repository_providers.dart';
import '../../presentation/customer_components.dart';
import 'china_address_detail_page.dart';

class PrepareChinaAddressPage extends ConsumerStatefulWidget {
  const PrepareChinaAddressPage({
    this.cargoMode = 'sea',
    this.containerId,
    this.airBookingId,
    super.key,
  });

  final String cargoMode;
  final String? containerId;
  final String? airBookingId;

  @override
  ConsumerState<PrepareChinaAddressPage> createState() => _PrepareChinaAddressPageState();
}

class _PrepareChinaAddressPageState extends ConsumerState<PrepareChinaAddressPage> {
  final _formKey = GlobalKey<FormState>();
  late String _cargoMode;
  String? _containerId;
  String? _airBookingId;
  final _destinationCountry = TextEditingController(text: 'Tanzania');
  final _destinationCity = TextEditingController();
  bool _busy = false;
  List<Map<String, dynamic>> _containers = [];
  List<Map<String, dynamic>> _airBookings = [];

  @override
  void initState() {
    super.initState();
    _cargoMode = widget.cargoMode;
    _containerId = widget.containerId;
    _airBookingId = widget.airBookingId;
    _load();
  }

  Future<void> _load() async {
    try {
      final results = await Future.wait([
        ref.read(customerContainersRepositoryProvider).listContainers(),
        ref.read(customerAirCargoRepositoryProvider).listBookings(),
      ]);
      setState(() {
        _containers = results[0].cast<Map<String, dynamic>>();
        _airBookings = results[1].cast<Map<String, dynamic>>();
      });
    } catch (_) {}
  }

  Future<void> _prepare() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      final address = await ref.read(customerChinaAddressesRepositoryProvider).ensureAddress(
        cargoMode: _cargoMode,
        destinationCountry: _destinationCountry.text.trim(),
        destinationCity: _destinationCity.text.trim(),
        containerId: _cargoMode == 'sea' ? _containerId : null,
        airBookingId: _cargoMode == 'air' ? _airBookingId : null,
      );
      if (mounted) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(
            builder: (_) => ChinaAddressDetailPage(addressId: address['id'].toString()),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not prepare address: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Prepare China address',
    body: Form(
      key: _formKey,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          const CustomerHeroCard(
            eyebrow: 'China forwarding',
            title: 'Prepare your China address',
            subtitle: 'Choose a valid booking service and destination. The warehouse is derived from that service.',
          ),
          const SizedBox(height: 24),
          DropdownButtonFormField<String>(
            initialValue: _cargoMode,
            decoration: const InputDecoration(labelText: 'Cargo mode'),
            items: const [
              DropdownMenuItem(value: 'sea', child: Text('Sea cargo')),
              DropdownMenuItem(value: 'air', child: Text('Air cargo')),
            ],
            onChanged: (v) => setState(() => _cargoMode = v ?? 'sea'),
          ),
          const SizedBox(height: 16),
          if (_cargoMode == 'sea')
            DropdownButtonFormField<String>(
              initialValue: _containerId,
              decoration: const InputDecoration(labelText: 'Selected booking'),
              items: [
                for (final c in _containers)
                  DropdownMenuItem(
                    value: c['id'].toString(),
                    child: Text('${c['origin'] ?? 'Origin'} → ${c['destination'] ?? 'Destination'}'),
                  ),
              ],
              onChanged: (v) => setState(() => _containerId = v),
              validator: (v) => v == null ? 'Select a booking' : null,
            )
          else
            DropdownButtonFormField<String>(
              initialValue: _airBookingId,
              decoration: const InputDecoration(labelText: 'Selected booking'),
              items: [
                for (final b in _airBookings)
                  DropdownMenuItem(
                    value: b['id'].toString(),
                    child: Text('${b['service_name'] ?? b['tracking_number'] ?? 'Air booking'}'),
                  ),
              ],
              onChanged: (v) => setState(() => _airBookingId = v),
              validator: (v) => v == null ? 'Select a booking' : null,
            ),
          const SizedBox(height: 16),
          TextFormField(
            controller: _destinationCountry,
            decoration: const InputDecoration(labelText: 'Destination country'),
            validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
          ),
          const SizedBox(height: 16),
          TextFormField(
            controller: _destinationCity,
            decoration: const InputDecoration(labelText: 'Destination city'),
            validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
          ),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: _busy ? null : _prepare,
            child: Text(_busy ? 'Preparing...' : 'Prepare address'),
          ),
        ],
      ),
    ),
  );
}
