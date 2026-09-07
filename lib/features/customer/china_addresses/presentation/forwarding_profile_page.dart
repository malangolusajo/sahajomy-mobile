import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../features/repository_providers.dart';
import '../../presentation/customer_components.dart';

class ForwardingProfilePage extends ConsumerStatefulWidget {
  const ForwardingProfilePage({this.fullName, this.phone, super.key});

  final String? fullName;
  final String? phone;

  @override
  ConsumerState<ForwardingProfilePage> createState() => _ForwardingProfilePageState();
}

class _ForwardingProfilePageState extends ConsumerState<ForwardingProfilePage> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _name;
  late final TextEditingController _phone;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _name = TextEditingController(text: widget.fullName ?? '');
    _phone = TextEditingController(text: widget.phone ?? '');
  }

  @override
  void dispose() {
    _name.dispose();
    _phone.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      await ref.read(customerChinaAddressesRepositoryProvider).updateForwardingProfile(
        fullName: _name.text.trim().isNotEmpty ? _name.text.trim() : null,
        phone: _phone.text.trim().isNotEmpty ? _phone.text.trim() : null,
      );
      if (mounted) {
        Navigator.of(context).pop(true);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not save: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Forwarding profile',
    body: Form(
      key: _formKey,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          const CustomerHeroCard(
            eyebrow: 'Account details',
            title: 'Forwarding profile',
            subtitle: 'Complete only missing customer details used to prepare forwarding addresses.',
          ),
          const SizedBox(height: 24),
          TextFormField(
            controller: _name,
            decoration: const InputDecoration(labelText: 'Full name'),
          ),
          const SizedBox(height: 16),
          TextFormField(
            controller: _phone,
            decoration: const InputDecoration(labelText: 'Phone / WhatsApp'),
            keyboardType: TextInputType.phone,
          ),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: _busy ? null : _save,
            child: Text(_busy ? 'Saving...' : 'Save missing details'),
          ),
        ],
      ),
    ),
  );
}
