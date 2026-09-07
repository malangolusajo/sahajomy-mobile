import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import '../../customer/presentation/customer_components.dart';
import '../../repository_providers.dart';
import '../../customer/air_cargo/data/customer_air_cargo_repository.dart';
import 'components/booking_step_indicator.dart';

class AirCargoDetailsPage extends ConsumerStatefulWidget {
  const AirCargoDetailsPage({
    required this.warehouseId,
    required this.cargoAdminId,
    required this.companyName,
    required this.warehouseName,
    super.key,
  });

  final String warehouseId;
  final String cargoAdminId;
  final String companyName;
  final String warehouseName;

  @override
  ConsumerState<AirCargoDetailsPage> createState() =>
      _AirCargoDetailsPageState();
}

class _AirCargoDetailsPageState extends ConsumerState<AirCargoDetailsPage> {
  final _form = GlobalKey<FormState>();
  final _weight = TextEditingController();
  final _destination = TextEditingController();
  final _country = TextEditingController();
  final _cartons = TextEditingController(text: '1');
  final _description = TextEditingController();

  String? _cargoTypeId;
  DateTime _shipmentDate = DateTime.now().add(const Duration(days: 1));
  final bool _busy = false;
  String? _error;
  List<Map<String, dynamic>> _cargoTypes = [];

  CustomerAirCargoRepository get _repo =>
      ref.read(customerAirCargoRepositoryProvider);

  @override
  void initState() {
    super.initState();
    _loadOptions();
  }

  @override
  void dispose() {
    _weight.dispose();
    _destination.dispose();
    _country.dispose();
    _cartons.dispose();
    _description.dispose();
    super.dispose();
  }

  Future<void> _loadOptions() async {
    try {
      final options = await _repo.options();
      if (!mounted) return;
      setState(() {
        _cargoTypes = (options['cargo_types'] as List? ?? const [])
            .whereType<Map>()
            .map((t) => Map<String, dynamic>.from(t))
            .toList();
      });
    } catch (_) {}
  }

  String? _required(String? v) =>
      v == null || v.trim().isEmpty ? 'This field is required.' : null;

  void _continueToReview() {
    if (!_form.currentState!.validate()) return;
    final params = {
      'warehouse_id': widget.warehouseId,
      'cargo_admin_id': widget.cargoAdminId,
      'company_name': widget.companyName,
      'warehouse_name': widget.warehouseName,
      'cargo_type_id': _cargoTypeId ?? '',
      'weight': _weight.text.trim(),
      'destination': _destination.text.trim(),
      'country': _country.text.trim(),
      'cartons': _cartons.text.trim(),
      'shipment_date': _shipmentDate.toIso8601String(),
      'description': _description.text.trim(),
    };
    context.push(
      '/customer/booking/air-review?${Uri(queryParameters: params).query}',
    );
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
        title: 'Cargo details',
        body: AbsorbPointer(
          absorbing: _busy,
          child: Form(
            key: _form,
            child: ListView(
              padding: const EdgeInsets.fromLTRB(24, 12, 24, 32),
              children: [
                const BookingStepIndicator(
                  steps: ['Service', 'Cargo details', 'Review'],
                  currentStep: 1,
                ),
                const SizedBox(height: 24),
                CustomerHeroCard(
                  eyebrow: 'Express Air Cargo',
                  title: 'Cargo details',
                  subtitle: '${widget.companyName} - ${widget.warehouseName}',
                ),
                const SizedBox(height: 24),
                DropdownButtonFormField<String>(
                  isExpanded: true,
                  initialValue: _cargoTypeId,
                  decoration:
                      const InputDecoration(labelText: 'Cargo type'),
                  items: _cargoTypes
                      .map((t) => DropdownMenuItem(
                            value: t['id']?.toString(),
                            child: Text('${t['name']}'),
                          ))
                      .toList(),
                  onChanged: (v) => setState(() => _cargoTypeId = v),
                  validator: (v) => v == null ? 'Select a cargo type.' : null,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _description,
                  maxLines: 3,
                  decoration: const InputDecoration(
                      labelText: 'Goods description'),
                  validator: _required,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _weight,
                  keyboardType:
                      const TextInputType.numberWithOptions(decimal: true),
                  decoration:
                      const InputDecoration(labelText: 'Weight (KG)'),
                  validator: (v) {
                    final value = double.tryParse(v ?? '');
                    if (value == null || !value.isFinite || value <= 0) {
                      return 'Enter a weight greater than zero.';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _cartons,
                  keyboardType: TextInputType.number,
                  decoration:
                      const InputDecoration(labelText: 'Carton count'),
                  validator: (v) {
                    return (int.tryParse(v ?? '') ?? 0) > 0
                        ? null
                        : 'Enter at least one carton.';
                  },
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _destination,
                  decoration: const InputDecoration(
                      labelText: 'Destination region'),
                  validator: _required,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _country,
                  decoration:
                      const InputDecoration(labelText: 'Destination country'),
                  validator: _required,
                ),
                const SizedBox(height: 16),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Shipment date'),
                  subtitle: Text(
                    '${_shipmentDate.year}-${_shipmentDate.month.toString().padLeft(2, '0')}-${_shipmentDate.day.toString().padLeft(2, '0')}',
                  ),
                  trailing: const Icon(Icons.calendar_today_outlined),
                  onTap: () async {
                    final date = await showDatePicker(
                      context: context,
                      firstDate: DateTime.now().add(const Duration(days: 1)),
                      lastDate:
                          DateTime.now().add(const Duration(days: 365)),
                      initialDate: _shipmentDate,
                    );
                    if (date != null) {
                      setState(() => _shipmentDate =
                          DateTime(date.year, date.month, date.day, 12));
                    }
                  },
                ),
                if (_error != null) ...[
                  const SizedBox(height: 16),
                  Text(_error!, style: const TextStyle(color: appError)),
                ],
                const SizedBox(height: 28),
                FilledButton(
                  onPressed: _busy ? null : _continueToReview,
                  child: const Text('Continue to review'),
                ),
                TextButton(
                  onPressed: _busy ? null : () => context.pop(),
                  child: const Text('Back to services'),
                ),
              ],
            ),
          ),
        ),
      );
}
