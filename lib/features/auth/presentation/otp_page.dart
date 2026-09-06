import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/auth/session.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/providers.dart';
import '../../../features/auth/data/auth_repository.dart';
import '../../../core/ui/sahajomy_ui.dart';

class OtpPage extends ConsumerStatefulWidget {
  const OtpPage({super.key, required this.phoneNumber});
  final String phoneNumber;

  @override
  ConsumerState<OtpPage> createState() => _OtpPageState();
}

class _OtpPageState extends ConsumerState<OtpPage> {
  final _codeController = TextEditingController();
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
      final authRepository = ref.read(authRepositoryProvider);
      final sessionStore = ref.read(sessionStoreProvider);
      final session = await authRepository.verifyOtp(
        phoneNumber: widget.phoneNumber,
        otpCode: _codeController.text.trim(),
      );
      await sessionStore.save(session);
      if (!mounted) return;
      final route = _routeFor(session.role);
      final pendingDestination = ref.read(pendingDestinationProvider);
      ref.read(pendingDestinationProvider.notifier).state = null;
      ref.invalidate(workspaceProvider);
      ref.invalidate(apiClientProvider);
      if (mounted) {
        context.go(pendingDestination ?? route);
      }
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
    appBar: const SahajomyScreenHeader(
      role: 'Customer',
      title: 'Verify your number',
    ),
    body: SafeArea(
      top: false,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
        children: [
          Text(
            'Enter verification code',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 8),
          Text('We sent a six-digit code to ${widget.phoneNumber}.'),
          const SizedBox(height: 28),
          const Text(
            'CUSTOMER',
            style: TextStyle(
              color: Color(0xFFFF6B4A),
              fontSize: 12,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.4,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Enter verification code',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 8),
          const Text('We sent a code to your phone number.'),
          const SizedBox(height: 24),
          TextField(
            controller: _codeController,
            keyboardType: TextInputType.number,
            textInputAction: TextInputAction.done,
            inputFormatters: [
              FilteringTextInputFormatter.digitsOnly,
              LengthLimitingTextInputFormatter(6),
            ],
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.w800,
              letterSpacing: 12,
            ),
            decoration: const InputDecoration(
              hintText: '000000',
              hintStyle: TextStyle(letterSpacing: 12),
            ),
            onSubmitted: (_) => _verify(),
          ),
          const SizedBox(height: 14),
          const Center(
            child: Text.rich(
              TextSpan(
                text: 'Didn\'t receive it? ',
                children: [
                  TextSpan(
                    text: 'Resend in 00:42',
                    style: TextStyle(
                      color: Color(0xFFE85A3A),
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ],
              ),
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
          const SizedBox(height: 28),
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
  );
}
