import 'package:flutter/material.dart';

import '../../presentation/customer_components.dart';
import 'review_sourcing_request_page.dart';

class RequestProductPage extends StatefulWidget {
  const RequestProductPage({required this.product, super.key});

  final Map<String, dynamic> product;

  @override
  State<RequestProductPage> createState() => _RequestProductPageState();
}

class _RequestProductPageState extends State<RequestProductPage> {
  final _formKey = GlobalKey<FormState>();
  final _quantity = TextEditingController(text: '1');
  final _color = TextEditingController();
  final _destination = TextEditingController(text: 'Dar es Salaam');
  final _notes = TextEditingController();

  @override
  void dispose() {
    _quantity.dispose();
    _color.dispose();
    _destination.dispose();
    _notes.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Request this product',
    body: Form(
      key: _formKey,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          TextFormField(
            controller: _quantity,
            decoration: const InputDecoration(labelText: 'Quantity'),
            keyboardType: TextInputType.number,
            validator: (v) => (v == null || int.tryParse(v) == null || int.parse(v) < 1) ? 'Enter a valid quantity' : null,
          ),
          const SizedBox(height: 16),
          TextFormField(
            controller: _color,
            decoration: const InputDecoration(labelText: 'Preferred color'),
          ),
          const SizedBox(height: 16),
          TextFormField(
            controller: _destination,
            decoration: const InputDecoration(labelText: 'Destination'),
            validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
          ),
          const SizedBox(height: 16),
          TextFormField(
            controller: _notes,
            decoration: const InputDecoration(labelText: 'Notes'),
            maxLines: 3,
          ),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: () {
              if (!_formKey.currentState!.validate()) return;
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => ReviewSourcingRequestPage(
                    product: widget.product,
                    quantity: int.parse(_quantity.text),
                    color: _color.text.trim(),
                    destination: _destination.text.trim(),
                    notes: _notes.text.trim(),
                  ),
                ),
              );
            },
            child: const Text('Continue to review'),
          ),
        ],
      ),
    ),
  );
}
