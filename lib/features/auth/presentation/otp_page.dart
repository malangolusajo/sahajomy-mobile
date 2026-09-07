import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/ui/core_flow_ui.dart';
import '../domain/otp_delivery.dart';
import '../../../core/auth/session.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/providers.dart';
import '../../../core/security/app_link_guard.dart';
import '../../../features/auth/data/auth_repository.dart';
import '../domain/auth_input.dart';

class OtpPage extends ConsumerStatefulWidget {
  const OtpPage({super.key});

  @override
  ConsumerState<OtpPage> createState() => _OtpPageState();
}

class _OtpPageState extends ConsumerState<OtpPage> {
  final _codeController = TextEditingController();
  var _isSubmitting = false;
  var _isResending = false;
  var _resendSeconds = 45;
  Timer? _resendTimer;
  bool _expired = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _startResendTimer();
  }

  void _startResendTimer() {
    _resendTimer?.cancel();
    _resendSeconds = 45;
    _resendTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) return;
      final expiry = ref.read(pendingOtpDeliveryProvider)?.expiresAt;
      if (!_expired &&
          !_isSubmitting &&
          !_isResending &&
          expiry != null &&
          !DateTime.now().isBefore(expiry)) {
        _expired = true;
        timer.cancel();
        context.go('/code-expired');
        return;
      }
      if (_resendSeconds <= 1) {
        if (_resendSeconds != 0) setState(() => _resendSeconds = 0);
      } else {
        setState(() => _resendSeconds--);
      }
    });
  }

  @override
  void dispose() {
    _codeController.dispose();
    _resendTimer?.cancel();
    super.dispose();
  }

  Future<void> _resend() async {
    if (_resendSeconds > 0 || _isResending || _isSubmitting) return;
    setState(() {
      _isResending = true;
      _errorMessage = null;
    });
    try {
      final phoneNumber = ref.read(pendingPhoneNumberProvider);
      if (phoneNumber == null) {
        if (mounted) context.go('/sign-in');
        return;
      }
      final delivery = await ref
          .read(authRepositoryProvider)
          .sendOtp(
            phoneNumber: phoneNumber,
            email: ref.read(pendingEmailProvider),
          );
      if (!mounted) return;
      ref.read(pendingOtpDeliveryProvider.notifier).state = delivery;
      _startResendTimer();
      setState(() => _isResending = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('A new verification code was sent to your email.'),
        ),
      );
    } on ApiException catch (error) {
      if (mounted) {
        setState(() {
          _isResending = false;
          _errorMessage = error.message;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _isResending = false;
          _errorMessage = 'Unable to resend the code. Please try again.';
        });
      }
    }
  }

  Future<void> _verify() async {
    if (_isSubmitting || _isResending) return;
    if (!isValidOtp(_codeController.text.trim())) {
      setState(
        () => _errorMessage = 'Enter the six-digit code from your email.',
      );
      return;
    }
    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });
    try {
      final phoneNumber = ref.read(pendingPhoneNumberProvider);
      if (phoneNumber == null) {
        if (mounted) context.go('/sign-in');
        return;
      }
      final authRepository = ref.read(authRepositoryProvider);
      final sessionStore = ref.read(sessionStoreProvider);
      final step = await authRepository.verifyOtp(
        phoneNumber: phoneNumber,
        otpCode: _codeController.text.trim(),
      );
      _codeController.clear();
      if (step is MfaRequired) {
        ref.read(pendingMfaChallengeProvider.notifier).state = step.challenge;
        if (mounted) context.go('/mfa');
        return;
      }
      final session = (step as Authenticated).session;
      await ref.read(workspaceProvider.notifier).clearWorkspace();
      await sessionStore.save(session);
      if (!mounted) return;
      final route = _routeFor(session.role);
      final pendingDestination = sanitizePendingDestination(
        ref.read(pendingDestinationProvider),
        role: session.role,
      );
      ref.read(pendingDestinationProvider.notifier).state = null;
      ref.read(pendingPhoneNumberProvider.notifier).state = null;
      ref.read(pendingEmailProvider.notifier).state = null;
      ref.read(pendingMfaChallengeProvider.notifier).state = null;
      ref.read(pendingOtpDeliveryProvider.notifier).state = null;
      if (mounted) {
        ref.read(pendingDestinationProvider.notifier).state =
            pendingDestination ?? route;
        context.go('/stay-updated');
      }
    } on ApiException catch (error) {
      if (!mounted) return;
      if (error.isGone) {
        context.go('/code-expired');
      } else if (error.message.toLowerCase().contains('account suspended')) {
        context.go('/account-suspended');
      } else {
        setState(() => _errorMessage = error.message);
      }
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
  Widget build(BuildContext context) => CoreFlowPage(
    title: 'Verify your code',
    onBack: () => context.go('/sign-in'),
    children: [
      CoreHero(
        eyebrow: 'SECURE SIGN IN',
        title: 'Verify your code',
        description: ref.watch(pendingOtpDeliveryProvider)?.maskedEmail != null
            ? 'Enter the code sent to ${ref.watch(pendingOtpDeliveryProvider)!.maskedEmail}.'
            : 'Enter the code sent to your registered email.',
      ),
      const SizedBox(height: 24),
      TextField(
        enabled: !_isSubmitting && !_isResending,
        controller: _codeController,
        keyboardType: TextInputType.number,
        textInputAction: TextInputAction.done,
        autofillHints: const [AutofillHints.oneTimeCode],
        inputFormatters: [
          FilteringTextInputFormatter.digitsOnly,
          LengthLimitingTextInputFormatter(6),
        ],
        textAlign: TextAlign.center,
        style: const TextStyle(
          fontSize: 28,
          fontWeight: FontWeight.w800,
          letterSpacing: 15,
          color: coreNavy,
        ),
        decoration: const InputDecoration(
          semanticCounterText: 'Six digit verification code',
          hintText: '• • • • • •',
          filled: false,
          border: InputBorder.none,
          enabledBorder: InputBorder.none,
          focusedBorder: UnderlineInputBorder(
            borderSide: BorderSide(color: coreNavy),
          ),
        ),
        onSubmitted: (_) => _verify(),
      ),
      const SizedBox(height: 12),
      Center(
        child: TextButton(
          onPressed: _resendSeconds == 0 && !_isResending && !_isSubmitting
              ? _resend
              : null,
          child: Text(
            _isResending
                ? 'Sending a new code…'
                : _resendSeconds > 0
                ? 'Resend in 00:${_resendSeconds.toString().padLeft(2, '0')}'
                : 'Resend code',
            style: const TextStyle(fontSize: 11, color: coreMuted),
          ),
        ),
      ),
      if (_errorMessage != null) CoreError(_errorMessage!),
      const SizedBox(height: 12),
      FilledButton(
        onPressed: _isSubmitting || _isResending ? null : _verify,
        child: Text(_isSubmitting ? 'Verifying…' : 'Verify & continue'),
      ),
    ],
  );
}
