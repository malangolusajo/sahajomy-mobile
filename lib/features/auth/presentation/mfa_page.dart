import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../../../app/theme.dart';
import '../../../core/auth/mfa_challenge.dart';
import '../../../core/auth/session.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/providers.dart';
import '../../../core/security/app_link_guard.dart';
import '../data/auth_repository.dart';
import '../domain/auth_input.dart';

class MfaPage extends ConsumerStatefulWidget {
  const MfaPage({super.key});

  @override
  ConsumerState<MfaPage> createState() => _MfaPageState();
}

class _MfaPageState extends ConsumerState<MfaPage> {
  final _codeController = TextEditingController();
  MfaChallenge? _challenge;
  bool _loadingSetup = false;
  bool _submitting = false;
  bool _showManualSecret = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) unawaited(_loadChallenge());
    });
  }

  Future<void> _loadChallenge() async {
    var challenge = ref.read(pendingMfaChallengeProvider);
    if (challenge == null) {
      if (mounted) context.go('/sign-in');
      return;
    }
    setState(() => _challenge = challenge);
    if (!challenge.setupRequired ||
        (challenge.otpAuthUri != null && challenge.manualSecret != null)) {
      return;
    }
    setState(() => _loadingSetup = true);
    try {
      challenge = await ref
          .read(authRepositoryProvider)
          .loadMfaSetup(challenge);
      ref.read(pendingMfaChallengeProvider.notifier).state = challenge;
      if (mounted) setState(() => _challenge = challenge);
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) {
        setState(
          () => _error = 'Unable to prepare multi-factor authentication.',
        );
      }
    } finally {
      if (mounted) setState(() => _loadingSetup = false);
    }
  }

  Future<void> _verify() async {
    if (_submitting) return;
    final challenge = _challenge;
    if (challenge == null || !isValidOtp(_codeController.text.trim())) {
      setState(() => _error = 'Enter the six-digit authenticator code.');
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final session = await ref
          .read(authRepositoryProvider)
          .verifyMfa(challenge: challenge, code: _codeController.text.trim());
      _codeController.clear();
      await ref.read(sessionStoreProvider).save(session);
      final destination = sanitizePendingDestination(
        ref.read(pendingDestinationProvider),
        role: session.role,
      );
      ref.read(pendingDestinationProvider.notifier).state = null;
      ref.read(pendingPhoneNumberProvider.notifier).state = null;
      ref.read(pendingMfaChallengeProvider.notifier).state = null;
      await ref.read(workspaceProvider.notifier).clearWorkspace();
      ref.read(pendingDestinationProvider.notifier).state =
          destination ?? _routeFor(session.role);
      if (mounted) context.go('/stay-updated');
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } on FormatException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) setState(() => _error = 'Unable to verify the code.');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  void _cancel() {
    _codeController.clear();
    ref.read(pendingPhoneNumberProvider.notifier).state = null;
    ref.read(pendingMfaChallengeProvider.notifier).state = null;
    context.go('/sign-in');
  }

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final challenge = _challenge;
    final uri = challenge?.otpAuthUri;
    final canShowQr =
        uri != null &&
        uri.length <= 2048 &&
        Uri.tryParse(uri)?.scheme.toLowerCase() == 'otpauth';
    final secret = challenge?.manualSecret;
    final canShowSecret =
        secret != null && RegExp(r'^[A-Za-z2-7 =-]{16,128}$').hasMatch(secret);

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (_, result) => _cancel(),
      child: Scaffold(
        appBar: AppBar(
          automaticallyImplyLeading: false,
          title: const Text('Two-step verification'),
          leading: IconButton(
            onPressed: _cancel,
            icon: const Icon(Icons.close_rounded),
          ),
        ),
        body: SafeArea(
          top: false,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(24, 24, 24, 32),
            children: [
              const Icon(Icons.security_rounded, size: 54, color: brandTeal),
              const SizedBox(height: 20),
              Text(
                challenge?.setupRequired == true
                    ? 'Protect this privileged account'
                    : 'Confirm it’s you',
                style: Theme.of(context).textTheme.headlineMedium,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 10),
              const Text(
                'Use your authenticator app to complete this secure sign-in.',
                textAlign: TextAlign.center,
              ),
              if (_loadingSetup) ...[
                const SizedBox(height: 28),
                const Center(child: CircularProgressIndicator()),
              ] else if (challenge?.setupRequired == true && canShowQr) ...[
                const SizedBox(height: 24),
                Center(
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: appBorder),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: QrImageView(data: uri, size: 210),
                    ),
                  ),
                ),
                if (canShowSecret) ...[
                  const SizedBox(height: 12),
                  TextButton.icon(
                    onPressed: () =>
                        setState(() => _showManualSecret = !_showManualSecret),
                    icon: Icon(
                      _showManualSecret
                          ? Icons.visibility_off_outlined
                          : Icons.visibility_outlined,
                    ),
                    label: Text(
                      _showManualSecret
                          ? 'Hide manual setup key'
                          : 'Show manual setup key',
                    ),
                  ),
                  if (_showManualSecret)
                    Semantics(
                      label: 'Authenticator setup key',
                      child: Text(
                        secret,
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          fontFamily: 'monospace',
                          fontWeight: FontWeight.w800,
                          letterSpacing: 2,
                        ),
                      ),
                    ),
                ],
              ],
              const SizedBox(height: 28),
              TextField(
                controller: _codeController,
                keyboardType: TextInputType.number,
                autofillHints: const [AutofillHints.oneTimeCode],
                textInputAction: TextInputAction.done,
                inputFormatters: [
                  FilteringTextInputFormatter.digitsOnly,
                  LengthLimitingTextInputFormatter(6),
                ],
                maxLength: 6,
                textAlign: TextAlign.center,
                decoration: const InputDecoration(
                  labelText: 'Authenticator code',
                  counterText: '',
                ),
                onSubmitted: (_) => _verify(),
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(
                  _error!,
                  style: const TextStyle(color: Color(0xFFB42318)),
                  textAlign: TextAlign.center,
                ),
              ],
              const SizedBox(height: 20),
              FilledButton(
                onPressed: _submitting || _loadingSetup ? null : _verify,
                child: _submitting
                    ? const SizedBox.square(
                        dimension: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Text('Verify securely'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

String _routeFor(UserRole role) => switch (role) {
  UserRole.customer => '/customer',
  UserRole.cargoAdmin => '/cargo-admin',
  UserRole.sourcingAgent => '/sourcing-agent',
  UserRole.superAdmin => '/super-admin',
};
