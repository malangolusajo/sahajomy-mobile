import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/network/api_exception.dart';
import '../../../core/providers.dart';
import '../../../core/ui/sahajomy_ui.dart';
import '../data/auth_repository.dart';
import '../domain/auth_input.dart';
import '../../public_services/presentation/official_information_page.dart';

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
      await ref
          .read(authRepositoryProvider)
          .sendOtp(
            phoneNumber: phone,
            name: _nameController.text.trim(),
            email: email,
          );
      if (!mounted) return;
      ref.read(pendingPhoneNumberProvider.notifier).state = phone;
      ref.read(pendingEmailProvider.notifier).state = email;
      context.go('/otp');
    } on ApiException catch (error) {
      if (mounted) setState(() => _errorMessage = error.message);
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
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(title: 'Create account'),
    body: SafeArea(
      top: false,
      child: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(24, 24, 24, 32),
          children: [
            const Align(alignment: Alignment.centerLeft, child: SahajomyBrandMark(size: 56)),
            const SizedBox(height: 24),
            Text(
              'Create your Sahajomy account',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 10),
            const Text(
              'Create one account for sourcing orders, cargo bookings and warehouse collections. We’ll email a code to verify your email address.',
            ),
            const SizedBox(height: 28),
            TextFormField(
              controller: _nameController,
              textCapitalization: TextCapitalization.words,
              textInputAction: TextInputAction.next,
              autofillHints: const [AutofillHints.name],
              inputFormatters: [LengthLimitingTextInputFormatter(120)],
              decoration: const InputDecoration(
                labelText: 'Full name',
                prefixIcon: Icon(Icons.person_outline_rounded),
              ),
              validator: (value) => value == null || value.trim().length < 2
                  ? 'Enter your full name.'
                  : null,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _emailController,
              keyboardType: TextInputType.emailAddress,
              textInputAction: TextInputAction.next,
              autofillHints: const [AutofillHints.email],
              autocorrect: false,
              inputFormatters: [LengthLimitingTextInputFormatter(254)],
              decoration: const InputDecoration(
                labelText: 'Email address',
                prefixIcon: Icon(Icons.email_outlined),
              ),
              validator: (value) {
                final email = value?.trim() ?? '';
                return RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$').hasMatch(email)
                    ? null
                    : 'Enter a valid email address.';
              },
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _phoneController,
              keyboardType: TextInputType.phone,
              textInputAction: TextInputAction.done,
              autofillHints: const [AutofillHints.telephoneNumber],
              inputFormatters: [
                FilteringTextInputFormatter.allow(RegExp(r'[0-9+ ()-]')),
                LengthLimitingTextInputFormatter(24),
              ],
              decoration: const InputDecoration(
                labelText: 'Mobile number',
                hintText: '+255 7XX XXX XXX',
                prefixIcon: Icon(Icons.phone_outlined),
              ),
              validator: (value) => value == null || !isValidPhoneNumber(value)
                  ? 'Enter a valid mobile number.'
                  : null,
              onFieldSubmitted: (_) => _continue(),
            ),
            if (_errorMessage != null) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(13),
                decoration: BoxDecoration(
                  color: const Color(0xFFFFF1F0),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  _errorMessage!,
                  style: const TextStyle(
                    color: Color(0xFFB42318),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
            const SizedBox(height: 24),
            FilledButton(
              onPressed: _isSubmitting ? null : _continue,
              child: _isSubmitting
                  ? const SizedBox.square(
                      dimension: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Text('Email my verification code'),
            ),
            const SizedBox(height: 14),
            const SahajomyLegalLinks(),
            Center(
              child: TextButton(
                onPressed: () => context.go('/sign-in'),
                child: const Text('Already have an account? Sign in'),
              ),
            ),
          ],
        ),
      ),
    ),
  );
}
