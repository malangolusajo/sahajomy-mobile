import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/network/api_exception.dart';
import '../../../core/providers.dart';
import '../../../core/ui/core_flow_ui.dart';
import '../domain/otp_delivery.dart';
import '../data/auth_repository.dart';
import '../domain/auth_input.dart';

class RegistrationPage extends ConsumerStatefulWidget {
  const RegistrationPage({super.key});

  @override
  ConsumerState<RegistrationPage> createState() => _RegistrationPageState();
}

class _RegistrationPageState extends ConsumerState<RegistrationPage> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _phoneController = TextEditingController();
  var _isSubmitting = false;
  String? _errorMessage;
  String? _emailError;
  String? _phoneError;

  @override
  void initState() {
    super.initState();
    _phoneController.text = ref.read(pendingPhoneNumberProvider) ?? '';
  }

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _phoneController.dispose();
    super.dispose();
  }

  Future<void> _continue() async {
    if (_isSubmitting || !_formKey.currentState!.validate()) return;
    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });
    try {
      final phone = normalizePhoneNumber(_phoneController.text);
      final email = _emailController.text.trim().toLowerCase();
      final delivery = await ref
          .read(authRepositoryProvider)
          .sendOtp(
            phoneNumber: phone,
            name: _nameController.text.trim(),
            email: email,
          );
      if (!mounted) return;
      ref.read(pendingOtpDeliveryProvider.notifier).state = delivery;
      ref.read(pendingPhoneNumberProvider.notifier).state = phone;
      ref.read(pendingEmailProvider.notifier).state = email;
      context.go('/otp');
    } on ApiException catch (error) {
      if (mounted) {
        setState(() {
          if (error.message.toLowerCase().contains('email')) {
            _emailError = error.message;
          } else if (error.message.toLowerCase().contains('phone')) {
            _phoneError = error.message;
          } else {
            _errorMessage = error.message;
          }
        });
      }
    } on FormatException catch (error) {
      if (mounted) setState(() => _errorMessage = error.message);
    } catch (_) {
      if (mounted) {
        setState(
          () => _errorMessage = 'We could not start your registration. Check your connection and try again.',
        );
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) => CoreFlowPage(
    title: 'Create your account',
    children: [
      const CoreHero(
        eyebrow: 'SAHAJOMY',
        title: 'Create your account',
        description: 'A few details are needed before we send your one-time verification code.',
      ),
      const SizedBox(height: 16),
      Form(
        key: _formKey,
        child: Column(
          children: [
            CoreField(
              label: 'Full name',
              child: TextFormField(
                enabled: !_isSubmitting,
                controller: _nameController,
                textCapitalization: TextCapitalization.words,
                autofillHints: const [AutofillHints.name],
                textInputAction: TextInputAction.next,
                decoration: const InputDecoration(hintText: 'Your full name'),
                validator: (v) => v == null || v.trim().isEmpty
                    ? 'Enter your full name.'
                    : null,
              ),
            ),
            CoreField(
              label: 'Email address',
              child: TextFormField(
                enabled: !_isSubmitting,
                controller: _emailController,
                forceErrorText: _emailError,
                onChanged: (_) {
                  if (_emailError != null) setState(() => _emailError = null);
                },
                keyboardType: TextInputType.emailAddress,
                autofillHints: const [AutofillHints.email],
                textInputAction: TextInputAction.next,
                autocorrect: false,
                decoration: const InputDecoration(hintText: 'name@example.com'),
                validator: (v) =>
                    RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
                        .hasMatch(v?.trim() ?? '')
                    ? null
                    : 'Enter a valid email address.',
              ),
            ),
            CoreField(
              label: 'Phone / WhatsApp',
              child: TextFormField(
                enabled: !_isSubmitting,
                controller: _phoneController,
                forceErrorText: _phoneError,
                onChanged: (_) {
                  if (_phoneError != null) setState(() => _phoneError = null);
                },
                keyboardType: TextInputType.phone,
                autofillHints: const [AutofillHints.telephoneNumber],
                inputFormatters: [
                  FilteringTextInputFormatter.allow(RegExp(r'[0-9+ ()-]')),
                  LengthLimitingTextInputFormatter(25),
                ],
                decoration: const InputDecoration(hintText: '+255 712 345 678'),
                validator: (v) => v == null || !isValidPhoneNumber(v)
                    ? 'Enter a valid mobile number.'
                    : null,
                onFieldSubmitted: (_) => _continue(),
              ),
            ),
          ],
        ),
      ),
      if (_errorMessage != null) CoreError(_errorMessage!),
      FilledButton(
        onPressed: _isSubmitting ? null : _continue,
        child: Text(_isSubmitting ? 'Sending code…' : 'Send verification code'),
      ),
      const SizedBox(height: 14),
      TextButton(
        onPressed: _isSubmitting ? null : () => context.go('/sign-in'),
        child: const Text('Already have an account? Sign in'),
      ),
    ],
  );
}
