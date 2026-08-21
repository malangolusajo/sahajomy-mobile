import 'package:flutter/material.dart';

import '../../../../core/network/api_exception.dart';
import '../data/customer_air_cargo_repository.dart';

class CreateAirCargoBookingPage extends StatefulWidget {
  const CreateAirCargoBookingPage({super.key});

  @override
  State<CreateAirCargoBookingPage> createState() =>
      _CreateAirCargoBookingPageState();
}

class _CreateAirCargoBookingPageState extends State<CreateAirCargoBookingPage> {
  final _formKey = GlobalKey<FormState>();
  final _repository = CustomerAirCargoRepository();
  final _weight = TextEditingController();
  final _destination = TextEditingController();
  final _cartons = TextEditingController(text: '1');
  final _description = TextEditingController();
  late Future<Map<String, dynamic>> _options = _repository.options();
  DateTime _shipmentDate = DateTime.now().add(const Duration(days: 1));
  String? _cargoTypeId;
  var _certified = false;
  var _submitting = false;
  String? _error;

  @override
  void dispose() {
    _weight.dispose();
    _destination.dispose();
    _cartons.dispose();
    _description.dispose();
    super.dispose();
  }

  Future<void> _submit(bool certificationRequired) async {
    if (!_formKey.currentState!.validate()) return;
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
      final result = await _repository.createBooking(
        cargoTypeId: _cargoTypeId!,
        weightKg: double.parse(_weight.text.trim()),
        shipmentDate: _shipmentDate,
        destinationRegion: _destination.text.trim(),
        cartonCount: int.parse(_cartons.text.trim()),
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
    appBar: AppBar(title: const Text('Book air cargo')),
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
        return Form(
          key: _formKey,
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              DropdownButtonFormField<String>(
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
                validator: (value) => (double.tryParse(value ?? '') ?? 0) > 0
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
                    : const Text('Create booking'),
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
