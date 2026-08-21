import 'package:flutter/material.dart';

import '../data/auth_repository.dart';
import '../../../core/network/api_exception.dart';
import 'otp_page.dart';

class SignInPage extends StatefulWidget {
  const SignInPage({super.key});

  @override
  State<SignInPage> createState() => _SignInPageState();
}

class _SignInPageState extends State<SignInPage> {
  final _formKey = GlobalKey<FormState>();
  final _phoneController = TextEditingController();
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _repository = AuthRepository();
  var _isSubmitting = false;
  String? _errorMessage;

  @override
  void dispose() {
    _phoneController.dispose();
    _nameController.dispose();
    _emailController.dispose();
    super.dispose();
  }

  Future<void> _sendOtp() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });
    try {
      await _repository.sendOtp(
        phoneNumber: _phoneController.text.trim(),
        name: _nameController.text.trim(),
        email: _emailController.text.trim(),
      );
      if (!mounted) return;
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => OtpPage(phoneNumber: _phoneController.text.trim()),
        ),
      );
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
    appBar: AppBar(),
    body: SafeArea(
      child: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            const Text(
              'CUSTOMER',
              style: TextStyle(
                fontSize: 11,
                letterSpacing: 1.3,
                fontWeight: FontWeight.w800,
                color: Color(0xFFFF6B4A),
              ),
            ),
            const SizedBox(height: 10),
            Text(
              'Welcome back',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 8),
            const Text(
              'Use your mobile number to receive a verification code.',
            ),
            const SizedBox(height: 28),
            TextFormField(
              controller: _phoneController,
              keyboardType: TextInputType.phone,
              autofillHints: const [AutofillHints.telephoneNumber],
              decoration: const InputDecoration(
                labelText: 'Mobile number',
                hintText: '+255 7XX XXX XXX',
              ),
              validator: (value) => value == null || value.trim().length < 7
                  ? 'Enter a valid mobile number.'
                  : null,
            ),
            const SizedBox(height: 20),
            Text(
              'New to Sahajomy?',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 4),
            const Text(
              'New accounts require your name and email before we can send the code.',
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _nameController,
              textCapitalization: TextCapitalization.words,
              decoration: const InputDecoration(
                labelText: 'Full name (new accounts)',
              ),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _emailController,
              keyboardType: TextInputType.emailAddress,
              autofillHints: const [AutofillHints.email],
              decoration: const InputDecoration(
                labelText: 'Email address (new accounts)',
              ),
            ),
            if (_errorMessage != null) ...[
              const SizedBox(height: 16),
              Text(
                _errorMessage!,
                style: const TextStyle(
                  color: Color(0xFFE11D48),
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
            const SizedBox(height: 24),
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
                  : const Text('Send verification code'),
            ),
          ],
        ),
      ),
    ),
  );
}
