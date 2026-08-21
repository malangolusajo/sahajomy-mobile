import 'package:flutter/material.dart';

import '../../../../core/network/api_exception.dart';
import '../data/customer_reservations_repository.dart';
import 'booking_confirmation_page.dart';

class ReserveContainerPage extends StatefulWidget {
  const ReserveContainerPage({super.key, required this.container});

  final Map<String, dynamic> container;

  @override
  State<ReserveContainerPage> createState() => _ReserveContainerPageState();
}

class _ReserveContainerPageState extends State<ReserveContainerPage> {
  final _formKey = GlobalKey<FormState>();
  final _cbmController = TextEditingController();
  final _destinationController = TextEditingController();
  final _cartonController = TextEditingController();
  final _repository = CustomerReservationsRepository();
  var _isSubmitting = false;
  String? _error;

  @override
  void dispose() {
    _cbmController.dispose();
    _destinationController.dispose();
    _cartonController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _isSubmitting = true;
      _error = null;
    });
    try {
      final result = await _repository.createReservation(
        containerId: widget.container['id'] as String,
        reservedCbm: double.parse(_cbmController.text.trim()),
        destinationRegion: _destinationController.text.trim(),
        cartonCount: int.tryParse(_cartonController.text.trim()),
      );
      if (!mounted) return;
      await Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => BookingConfirmationPage(reservation: result),
        ),
      );
      if (mounted) Navigator.pop(context, true);
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) {
        setState(
          () => _error = 'Unable to reserve container space. Try again.',
        );
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final available = widget.container['available_cbm'];
    return Scaffold(
      appBar: AppBar(title: const Text('Reserve container space')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Card(
              child: ListTile(
                leading: const Icon(Icons.inventory_2_outlined),
                title: Text(
                  '${widget.container['container_size'] ?? 'Container'}: ${widget.container['origin'] ?? 'Origin'} to ${widget.container['destination'] ?? 'Destination'}',
                  style: const TextStyle(fontWeight: FontWeight.w800),
                ),
                subtitle: Text('Available space: $available CBM'),
              ),
            ),
            const SizedBox(height: 20),
            TextFormField(
              controller: _cbmController,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              decoration: const InputDecoration(
                labelText: 'Space required (CBM)',
              ),
              validator: (value) {
                final cbm = double.tryParse(value?.trim() ?? '');
                final maximum = available is num ? available.toDouble() : null;
                if (cbm == null || cbm <= 0) return 'Enter a valid CBM amount.';
                if (maximum != null && cbm > maximum) {
                  return 'Only $maximum CBM is currently available.';
                }
                return null;
              },
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _destinationController,
              textCapitalization: TextCapitalization.words,
              decoration: const InputDecoration(
                labelText: 'Destination region or city',
              ),
              validator: (value) => value == null || value.trim().isEmpty
                  ? 'Enter the delivery destination.'
                  : null,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _cartonController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Carton count (optional)',
              ),
              validator: (value) {
                if (value == null || value.trim().isEmpty) return null;
                return int.tryParse(value.trim()) == null
                    ? 'Enter a whole number.'
                    : null;
              },
            ),
            if (_error != null) ...[
              const SizedBox(height: 16),
              Text(_error!, style: const TextStyle(color: Color(0xFFE11D48))),
            ],
            const SizedBox(height: 28),
            FilledButton(
              onPressed: _isSubmitting ? null : _submit,
              child: _isSubmitting
                  ? const SizedBox.square(
                      dimension: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Text('Reserve space'),
            ),
          ],
        ),
      ),
    );
  }
}
