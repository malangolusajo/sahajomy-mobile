import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import '../../../core/ui/core_flow_ui.dart';
import '../../../core/ui/sahajomy_ui.dart';
import '../domain/otp_delivery.dart';
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
  final _emailController = TextEditingController();
  bool _needsEmail = false;
  var _isSubmitting = false;
  String? _errorMessage;

  @override
  void dispose() {
    _phoneController.dispose();
    _emailController.dispose();
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
      final delivery = await authRepository.sendOtp(
        phoneNumber: phone,
        email: _needsEmail ? _emailController.text.trim().toLowerCase() : null,
      );
      if (!mounted) return;
      ref.read(pendingOtpDeliveryProvider.notifier).state = delivery;
      ref.read(pendingPhoneNumberProvider.notifier).state = phone;
      ref.read(pendingEmailProvider.notifier).state = _needsEmail
          ? _emailController.text.trim().toLowerCase()
          : null;
      context.go('/otp');
    } on ApiException catch (error) {
      if (!mounted) return;
      if (error.message ==
          'Name and email are required for new user registration.') {
        ref.read(pendingPhoneNumberProvider.notifier).state =
            normalizePhoneNumber(_phoneController.text);
        context.push('/register');
      } else if (error.message.toLowerCase().contains('account suspended')) {
        context.push('/account-suspended');
      } else if (error.message ==
          'Email is required for this user. Please provide your email to continue.') {
        setState(() {
          _needsEmail = true;
          _errorMessage = error.message;
        });
      } else {
        setState(() => _errorMessage = error.message);
      }
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
  Widget build(BuildContext context) => CoreFlowPage(
    title: 'Sign in',
    canGoBack: false,
    children: [
      ClipRRect(
        borderRadius: BorderRadius.circular(26),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.all(24),
          decoration: const BoxDecoration(
            color: Color(0xFF0B2A40),
          ),
          child: Stack(
            children: [
              Positioned(
                top: -80,
                right: -60,
                child: Container(
                  width: 220,
                  height: 220,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: const Color(0xFF1FAD77).withValues(alpha: 0.18),
                  ),
                ),
              ),
              Positioned(
                bottom: -100,
                left: -40,
                child: Container(
                  width: 180,
                  height: 180,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: const Color(0xFF0F3D5E).withValues(alpha: 0.5),
                  ),
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SahajomyBrandMark(size: 44, showShadow: false),
                  const SizedBox(height: 20),
                  const Text(
                    'Ship, source, and track\ngoods from China to Africa',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 24,
                      height: 1.2,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'Get a China warehouse address, source products, book sea or air cargo, and track shipments from China to Africa with Sahajomy.',
                    style: TextStyle(
                      color: Color(0xFFD1DEE6),
                      fontSize: 14,
                      height: 1.55,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
      const SizedBox(height: 16),
      Form(
        key: _formKey,
        child: Column(
          children: [
            CoreField(
              label: 'Phone / WhatsApp number',
              child: TextFormField(
                enabled: !_isSubmitting,
                controller: _phoneController,
                keyboardType: TextInputType.phone,
                textInputAction: TextInputAction.done,
                autofillHints: const [AutofillHints.telephoneNumber],
                inputFormatters: [
                  FilteringTextInputFormatter.allow(RegExp(r'[0-9+ ()-]')),
                  LengthLimitingTextInputFormatter(25),
                ],
                decoration: const InputDecoration(hintText: '+255 7•• ••• •••'),
                validator: (value) =>
                    value == null || !isValidPhoneNumber(value)
                    ? 'Enter a valid mobile number.'
                    : null,
                onFieldSubmitted: (_) => _sendOtp(),
              ),
            ),
            if (_needsEmail)
              CoreField(
                label: 'Email address',
                child: TextFormField(
                  controller: _emailController,
                  enabled: !_isSubmitting,
                  keyboardType: TextInputType.emailAddress,
                  autofillHints: const [AutofillHints.email],
                  decoration: const InputDecoration(
                    hintText: 'name@example.com',
                  ),
                  validator: (value) =>
                      RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
                          .hasMatch(value?.trim() ?? '')
                      ? null
                      : 'Enter a valid email address.',
                  onFieldSubmitted: (_) => _sendOtp(),
                ),
              ),
          ],
        ),
      ),
      if (_errorMessage != null) CoreError(_errorMessage!),
      FilledButton(
        onPressed: _isSubmitting ? null : _sendOtp,
        child: Text(_isSubmitting ? 'Sending code…' : 'Continue'),
      ),
      const SizedBox(height: 16),
      Container(
        padding: const EdgeInsets.all(12),
        decoration: const BoxDecoration(
          color: Color(0xFFFFFAEA),
          border: Border(left: BorderSide(color: Color(0xFFEAB91E), width: 4)),
        ),
        child: const Text(
          'New here? We will ask for your name and email before sending the verification code.',
          style: TextStyle(fontSize: 11, color: Color(0xFF6B520D)),
        ),
      ),
      TextButton(
        onPressed: _isSubmitting ? null : () => context.push('/register'),
        child: const Text('Create an account'),
      ),
      const SahajomyLegalLinks(),
      const SizedBox(height: 8),
      Text(
        '\u00a9 ${DateTime.now().year} Sahajomy. All rights reserved.',
        textAlign: TextAlign.center,
        style: const TextStyle(fontSize: 11, color: appMuted),
      ),
    ],
  );
}
