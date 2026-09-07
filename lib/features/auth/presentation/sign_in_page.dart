import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import '../../../core/ui/sahajomy_ui.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/providers.dart';
import '../../../features/auth/data/auth_repository.dart';
import '../domain/auth_input.dart';
import '../../public_services/presentation/official_information_page.dart';

class SignInPage extends ConsumerStatefulWidget {
  const SignInPage({super.key});

  @override
  ConsumerState<SignInPage> createState() => _SignInPageState();
}

class _SignInPageState extends ConsumerState<SignInPage> {
  final _formKey = GlobalKey<FormState>();
  final _phoneController = TextEditingController();
  var _isSubmitting = false;
  String? _errorMessage;

  @override
  void dispose() {
    _phoneController.dispose();
    super.dispose();
  }

  Future<void> _sendOtp() async {
    if (_isSubmitting || !_formKey.currentState!.validate()) return;
    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });
    try {
      final authRepository = ref.read(authRepositoryProvider);
      final phone = normalizePhoneNumber(_phoneController.text);
      await authRepository.sendOtp(phoneNumber: phone);
      if (!mounted) return;
      ref.read(pendingPhoneNumberProvider.notifier).state = phone;
      ref.read(pendingEmailProvider.notifier).state = null;
      context.go('/otp');
    } on ApiException catch (error) {
      if (mounted) setState(() => _errorMessage = error.message);
    } on FormatException catch (error) {
      if (mounted) setState(() => _errorMessage = error.message);
    } catch (_) {
      if (mounted) {
        setState(
          () => _errorMessage = 'Unable to contact Sahajomy. Check your connection and try again.',
        );
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(title: 'Secure sign in'),
    body: SafeArea(
      top: false,
      child: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(24, 24, 24, 32),
          children: [
            const Align(alignment: Alignment.centerLeft, child: SahajomyBrandMark(size: 58)),
            const SizedBox(height: 28),
            Text(
              'Your shipping account',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 10),
            const Text(
              'Enter the mobile number linked to your account. We\'ll email a one-time verification code to your registered email address.',
            ),
            const SizedBox(height: 30),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(18),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Mobile number',
                      style: TextStyle(
                        color: appInk,
                        fontSize: 13,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 10),
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
                        hintText: '+255 7XX XXX XXX',
                        prefixIcon: Icon(Icons.phone_rounded),
                      ),
                      validator: (value) =>
                          value == null || !isValidPhoneNumber(value)
                              ? 'Enter a valid mobile number.'
                              : null,
                      onFieldSubmitted: (_) => _sendOtp(),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(
                          Icons.lock_outline_rounded,
                          size: 17,
                          color: brandTeal,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            'Verification codes are sent to your registered email.',
                            style: TextStyle(fontSize: 12, height: 1.4, color: appMuted),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            if (_errorMessage != null) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(13),
                decoration: BoxDecoration(
                  color: appErrorLight,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  _errorMessage!,
                  style: const TextStyle(
                    color: appError,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
            const SizedBox(height: 22),
            FilledButton(
              onPressed: _isSubmitting ? null : _sendOtp,
              child: _isSubmitting
                  ? const SizedBox.square(
                      dimension: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Text('Email me a verification code'),
            ),
            const SizedBox(height: 14),
            Center(
              child: TextButton(
                onPressed: () => context.push('/register'),
                child: const Text('New to Sahajomy? Create an account'),
              ),
            ),
            const SizedBox(height: 8),
            const SahajomyLegalLinks(),
          ],
        ),
      ),
    ),
  );
}