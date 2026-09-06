import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
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
  var _isResending = false;
  var _resendSeconds = 45;
  Timer? _resendTimer;
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
      if (_resendSeconds <= 1) {
        timer.cancel();
        setState(() => _resendSeconds = 0);
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
    if (_resendSeconds > 0 || _isResending) return;
    setState(() {
      _isResending = true;
      _errorMessage = null;
    });
    try {
      await ref
          .read(authRepositoryProvider)
          .sendOtp(phoneNumber: widget.phoneNumber);
      if (!mounted) return;
      _startResendTimer();
      setState(() => _isResending = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('A new verification code was sent.')),
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
    appBar: const SahajomyScreenHeader(title: 'Verify your number'),
    body: SafeArea(
      top: false,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(24, 24, 24, 32),
        children: [
          Container(
            width: 58,
            height: 58,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: const Color(0xFFFFE9E3),
              borderRadius: BorderRadius.circular(18),
            ),
            child: const Icon(Icons.sms_outlined, color: brandCoral, size: 28),
          ),
          const SizedBox(height: 26),
          Text(
            'Enter verification code',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 10),
          Text.rich(
            TextSpan(
              text: 'We sent a six-digit code to ',
              children: [
                TextSpan(
                  text: widget.phoneNumber,
                  style: const TextStyle(
                    color: appInk,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 30),
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
              fontSize: 26,
              fontWeight: FontWeight.w900,
              letterSpacing: 10,
            ),
            decoration: const InputDecoration(
              hintText: '000000',
              hintStyle: TextStyle(letterSpacing: 10),
              counterText: '',
            ),
            maxLength: 6,
            onSubmitted: (_) => _verify(),
          ),
          const SizedBox(height: 10),
          Center(
            child: TextButton(
              onPressed: _resendSeconds == 0 && !_isResending ? _resend : null,
              child: Text(
                _isResending
                    ? 'Sending a new code…'
                    : _resendSeconds > 0
                    ? 'Resend available in 0:${_resendSeconds.toString().padLeft(2, '0')}'
                    : 'Resend verification code',
              ),
            ),
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
