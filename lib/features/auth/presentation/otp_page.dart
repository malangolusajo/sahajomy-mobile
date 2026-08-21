import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../data/auth_repository.dart';
import '../../../core/auth/session.dart';
import '../../../core/auth/session_store.dart';
import '../../../core/network/api_exception.dart';

class OtpPage extends StatefulWidget {
  const OtpPage({super.key, required this.phoneNumber});
  final String phoneNumber;

  @override
  State<OtpPage> createState() => _OtpPageState();
}

class _OtpPageState extends State<OtpPage> {
  final _codeController = TextEditingController();
  final _repository = AuthRepository();
  final _sessionStore = SessionStore();
  var _isSubmitting = false;
  String? _errorMessage;

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _verify() async {
    if (_codeController.text.trim().length < 4) {
      setState(
        () => _errorMessage = 'Enter the verification code we sent you.',
      );
      return;
    }
    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });
    try {
      final session = await _repository.verifyOtp(
        phoneNumber: widget.phoneNumber,
        otpCode: _codeController.text.trim(),
      );
      await _sessionStore.save(session);
      if (!mounted) return;
      Navigator.of(context)
          .pushNamedAndRemoveUntil(_routeFor(session.role), (_) => false);
    } on ApiException catch (error) {
      if (mounted) setState(() => _errorMessage = error.message);
    } on FormatException catch (error) {
      if (mounted) setState(() => _errorMessage = error.message);
    } catch (_) {
      if (mounted) {
        setState(
          () => _errorMessage = 'Unable to verify the code. Please try again.',
        );
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  String _routeFor(UserRole role) => switch (role) {
    UserRole.customer => '/customer',
    UserRole.cargoAdmin => '/cargo-admin',
    UserRole.sourcingAgent => '/sourcing-agent',
    UserRole.superAdmin => '/super-admin',
  };

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(),
    body: SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Verify your number',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 8),
            Text('Enter the code sent to ${widget.phoneNumber}.'),
            const SizedBox(height: 28),
            TextField(
              controller: _codeController,
              keyboardType: TextInputType.number,
              textInputAction: TextInputAction.done,
              inputFormatters: [
                FilteringTextInputFormatter.digitsOnly,
                LengthLimitingTextInputFormatter(8),
              ],
              decoration: const InputDecoration(
                labelText: 'Verification code',
                hintText: '000000',
              ),
              onSubmitted: (_) => _verify(),
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
            const Spacer(),
            FilledButton(
              onPressed: _isSubmitting ? null : _verify,
              child: _isSubmitting
                  ? const SizedBox.square(
                      dimension: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Text('Verify and continue'),
            ),
          ],
        ),
      ),
    ),
  );
}
