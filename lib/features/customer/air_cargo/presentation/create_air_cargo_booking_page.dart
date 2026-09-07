import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sahajomy_mobile/features/repository_providers.dart';

import '../../../../core/network/api_exception.dart';
import '../../../../core/ui/logistics_ui.dart';
import '../../../../core/ui/sahajomy_ui.dart';
import '../data/customer_air_cargo_repository.dart';

class CreateAirCargoBookingPage extends ConsumerStatefulWidget {
  const CreateAirCargoBookingPage({super.key});

  @override
  ConsumerState<CreateAirCargoBookingPage> createState() =>
      _CreateAirCargoBookingPageState();
}

class _CreateAirCargoBookingPageState
    extends ConsumerState<CreateAirCargoBookingPage> {
  final _formKey = GlobalKey<FormState>();
  CustomerAirCargoRepository get _repository =>
      ref.read(customerAirCargoRepositoryProvider);
  final _weight = TextEditingController();
  final _destination = TextEditingController();
  final _country = TextEditingController();
  final _cartons = TextEditingController(text: '1');
  final _description = TextEditingController();
  late Future<Map<String, dynamic>> _options = Future.microtask(
    () => _repository.options(),
  );
  DateTime _shipmentDate = DateTime.now().add(const Duration(days: 1));
  String? _cargoTypeId;
  Map<String, dynamic>? _service;
  var _certified = false;
  var _submitting = false;
  String? _error;

  @override
  void dispose() {
    _weight.dispose();
    _destination.dispose();
    _country.dispose();
    _cartons.dispose();
    _description.dispose();
    super.dispose();
  }

  Future<void> _submit(bool certificationRequired) async {
    if (_submitting || !_formKey.currentState!.validate()) return;
    if (certificationRequired && !_certified) {
      setState(
        () => _error =
            'Confirm that the required import certification is available.',
      );
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final address = await _repository.prepareAddress(city: _destination.text.trim(), country: _country.text.trim(), cargoAdminId: '${_service!['cargo_admin_id']}', warehouseId: '${_service!['warehouse_id']}');
      if (!mounted) return;
      final confirmed = await showDialog<bool>(context: context, builder: (context) => AlertDialog(
        title: const Text('Review air cargo booking'),
        content: SingleChildScrollView(child: SahajomyKeyValueList(entries: {
          'Cargo company': _service!['cargo_admin_name'], 'Warehouse': _service!['warehouse_name'],
          'Weight': '${_weight.text} kg', 'Destination': '${_destination.text}, ${_country.text}',
          'Cartons': _cartons.text, 'Shipment date': logisticsDate(_shipmentDate.toIso8601String()),
          'Supplier shipping mark': (address['copy'] as Map?)?['shipping_mark'] ?? address['shipping_mark'],
          'Freight rate': 'Quotation required',
        })),
        actions: [TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Edit cargo details')), FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Confirm air booking'))],
      ));
      if (confirmed != true || !mounted) return;
      final result = await _repository.createBooking(
        cargoTypeId: _cargoTypeId!,
        weightKg: double.parse(_weight.text.trim()),
        shipmentDate: _shipmentDate,
        destinationRegion: _destination.text.trim(),
        cartonCount: int.parse(_cartons.text.trim()),
        destinationCountry: _country.text.trim(),
        cargoAdminId: '${_service!['cargo_admin_id']}', warehouseId: '${_service!['warehouse_id']}', chinaAddressId: '${address['id']}',
        cargoDescription: _description.text.trim(),
        certificationAcknowledged: _certified,
      );
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Air cargo booked'),
          content: Text(
            'Tracking number: ${result['tracking_number'] ?? 'Pending'}',
          ),
          actions: [
            FilledButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Done'),
            ),
          ],
        ),
      );
      if (mounted) {
        Navigator.pop(context, true);
      }
    } on ApiException catch (error) {
      if (mounted) {
        setState(() => _error = error.message);
      }
    } catch (_) {
      if (mounted) {
        setState(() => _error = 'Unable to create this booking. Try again.');
      }
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(title: 'Book air cargo'),
    body: FutureBuilder<Map<String, dynamic>>(
      future: _options,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return Center(
            child: OutlinedButton(
              onPressed: () => setState(() => _options = _repository.options()),
              child: const Text('Try again'),
            ),
          );
        }
        final types = (snapshot.data!['cargo_types'] as List? ?? const [])
            .cast<Map<String, dynamic>>();
        final selected = types
            .where((type) => type['id'] == _cargoTypeId)
            .firstOrNull;
        final policy = selected?['shipping_policy'] as Map?;
        final certificationRequired = policy?['requires_certification'] == true;
        final services = (snapshot.data!['services'] as List? ?? const []).whereType<Map>().map((s) => Map<String, dynamic>.from(s)).toList();
        return Form(
          key: _formKey,
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              const LogisticsIntro(eyebrow: 'Express Air Cargo', title: 'Arrange your air shipment', description: 'Choose a cargo company and China warehouse, then review your cargo before booking.'),
              DropdownButtonFormField<String>(
                isExpanded: true,
                initialValue: _service?['warehouse_id']?.toString(),
                decoration: const InputDecoration(labelText: 'Cargo company & China warehouse'),
                items: services.map((s) => DropdownMenuItem(value: '${s['warehouse_id']}', child: Text('${s['cargo_admin_name']} · ${s['warehouse_name']}', maxLines: 2, overflow: TextOverflow.ellipsis))).toList(),
                onChanged: _submitting ? null : (id) => setState(() => _service = services.firstWhere((s) => '${s['warehouse_id']}' == id)),
                validator: (value) => value == null ? 'Choose a cargo company and warehouse.' : null,
              ),
              const SizedBox(height: 20),
              DropdownButtonFormField<String>(
                isExpanded: true,
                initialValue: _cargoTypeId,
                decoration: const InputDecoration(labelText: 'Cargo type'),
                items: types
                    .map(
                      (type) => DropdownMenuItem(
                        value: type['id'] as String,
                        child: Text(type['name'] as String),
                      ),
                    )
                    .toList(),
                onChanged: (value) => setState(() {
                  _cargoTypeId = value;
                  _certified = false;
                }),
                validator: (value) =>
                    value == null ? 'Select a cargo type.' : null,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _weight,
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
                decoration: const InputDecoration(labelText: 'Weight (KG)'),
                validator: (value) => (double.tryParse(value ?? '') ?? 0) > 0 && (double.tryParse(value ?? '')?.isFinite ?? false)
                    ? null
                    : 'Enter a weight greater than zero.',
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _destination,
                decoration: const InputDecoration(
                  labelText: 'Destination region',
                ),
                validator: (value) => value == null || value.trim().isEmpty
                    ? 'Enter a destination.'
                    : null,
              ),
              const SizedBox(height: 16),
              TextFormField(controller: _country, maxLength: 100, decoration: const InputDecoration(labelText: 'Destination country'), validator: (value) => value == null || value.trim().length < 2 ? 'Enter a destination country.' : null),
              TextFormField(
                controller: _cartons,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Carton count'),
                validator: (value) => (int.tryParse(value ?? '') ?? 0) > 0
                    ? null
                    : 'Enter at least one carton.',
              ),
              const SizedBox(height: 16),
              ListTile(
                title: const Text('Shipment date'),
                subtitle: Text(
                  '${_shipmentDate.year}-${_shipmentDate.month.toString().padLeft(2, '0')}-${_shipmentDate.day.toString().padLeft(2, '0')}',
                ),
                trailing: const Icon(Icons.calendar_today_outlined),
                onTap: () async {
                  final date = await showDatePicker(
                    context: context,
                    firstDate: DateTime.now().add(const Duration(days: 1)),
                    lastDate: DateTime.now().add(const Duration(days: 365)),
                    initialDate: _shipmentDate,
                  );
                  if (date != null) {
                    setState(
                      () => _shipmentDate = DateTime(
                        date.year,
                        date.month,
                        date.day,
                        12,
                      ),
                    );
                  }
                },
              ),
              TextFormField(
                controller: _description,
                maxLines: 3,
                decoration: const InputDecoration(
                  labelText: 'Cargo description (optional)',
                ),
              ),
              if (certificationRequired)
                CheckboxListTile(
                  value: _certified,
                  onChanged: (value) =>
                      setState(() => _certified = value ?? false),
                  title: const Text('I have the required import certification'),
                ),
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.only(top: 16),
                  child: Text(
                    _error!,
                    style: const TextStyle(color: Color(0xFFE11D48)),
                  ),
                ),
              const SizedBox(height: 24),
              FilledButton(
                onPressed: _submitting
                    ? null
                    : () => _submit(certificationRequired),
                child: _submitting
                    ? const SizedBox.square(
                        dimension: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Text('Review air cargo booking'),
              ),
            ],
          ),
        );
      },
    ),
  );
}

extension<T> on Iterable<T> {
  T? get firstOrNull => isEmpty ? null : first;
}
