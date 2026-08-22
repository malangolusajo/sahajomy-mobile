import 'package:flutter/material.dart';

import '../../../core/ui/sahajomy_ui.dart';
import '../data/workflow_api_repository.dart';

class ApiFormField {
  const ApiFormField({
    required this.name,
    required this.label,
    this.required = false,
    this.numeric = false,
    this.multiline = false,
  });

  final String name;
  final String label;
  final bool required;
  final bool numeric;
  final bool multiline;
}

/// A schema-aligned API form used for workflows defined by the backend contract.
class ApiFormPage extends StatefulWidget {
  const ApiFormPage({
    required this.role,
    required this.title,
    required this.endpoint,
    required this.fields,
    this.multipart = false,
    super.key,
  });

  final String role;
  final String title;
  final String endpoint;
  final List<ApiFormField> fields;
  final bool multipart;

  @override
  State<ApiFormPage> createState() => _ApiFormPageState();
}

class _ApiFormPageState extends State<ApiFormPage> {
  final _repository = WorkflowApiRepository();
  final _formKey = GlobalKey<FormState>();
  late final Map<String, TextEditingController> _controllers = {
    for (final field in widget.fields) field.name: TextEditingController(),
  };
  var _submitting = false;

  @override
  void dispose() {
    for (final controller in _controllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _submitting = true);
    try {
      final strings = {
        for (final field in widget.fields)
          if (_controllers[field.name]!.text.trim().isNotEmpty)
            field.name: _controllers[field.name]!.text.trim(),
      };
      if (widget.multipart) {
        await _repository.submitForm(widget.endpoint, strings);
      } else {
        final payload = <String, dynamic>{
          for (final field in widget.fields)
            if (strings.containsKey(field.name))
              field.name: field.numeric
                  ? num.parse(strings[field.name]!)
                  : strings[field.name],
        };
        await _repository.submit(widget.endpoint, payload);
      }
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${widget.title} submitted successfully.')),
      );
      Navigator.maybePop(context, true);
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('The request could not be submitted.')),
      );
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: SahajomyScreenHeader(role: widget.role, title: widget.title),
    body: Form(
      key: _formKey,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
        children: [
          Text(widget.title, style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 6),
          const Text('Complete the required details and submit them securely.'),
          const SizedBox(height: 20),
          for (final field in widget.fields) ...[
            TextFormField(
              controller: _controllers[field.name],
              keyboardType: field.numeric
                  ? const TextInputType.numberWithOptions(decimal: true)
                  : field.name == 'email'
                  ? TextInputType.emailAddress
                  : TextInputType.text,
              maxLines: field.multiline ? 4 : 1,
              decoration: InputDecoration(
                labelText: '${field.label}${field.required ? ' *' : ''}',
              ),
              validator: (value) {
                if (field.required && (value == null || value.trim().isEmpty)) {
                  return '${field.label} is required.';
                }
                if (field.numeric &&
                    value != null &&
                    value.isNotEmpty &&
                    num.tryParse(value) == null) {
                  return 'Enter a valid number.';
                }
                return null;
              },
            ),
            const SizedBox(height: 14),
          ],
          const SizedBox(height: 8),
          FilledButton(
            onPressed: _submitting ? null : _submit,
            child: Text(_submitting ? 'Submitting...' : 'Submit'),
          ),
        ],
      ),
    ),
  );
}
