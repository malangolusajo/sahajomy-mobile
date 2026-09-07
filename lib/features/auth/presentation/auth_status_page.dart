import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/providers.dart';
import '../../../core/ui/core_flow_ui.dart';
import '../data/auth_repository.dart';
import '../domain/otp_delivery.dart';

class AuthStatusPage extends ConsumerStatefulWidget {
  const AuthStatusPage({super.key, this.suspended = false});
  final bool suspended;
  @override
  ConsumerState<AuthStatusPage> createState() => _AuthStatusPageState();
}

class _AuthStatusPageState extends ConsumerState<AuthStatusPage> {
  bool _busy = false;
  String? _error;
  Future<void> _continue() async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      if (widget.suspended) {
        if (!await launchUrl(
          Uri.parse('https://sahajomy.co.tz/contact'),
          mode: LaunchMode.externalApplication,
        )) {
          throw const FormatException(
            'Open sahajomy.co.tz/contact in your browser to contact support.',
          );
        }
      } else {
        final phone = ref.read(pendingPhoneNumberProvider);
        if (phone == null) {
          if (mounted) context.go('/sign-in');
          return;
        }
        final delivery = await ref
            .read(authRepositoryProvider)
            .sendOtp(phoneNumber: phone, email: ref.read(pendingEmailProvider));
        ref.read(pendingOtpDeliveryProvider.notifier).state = delivery;
        if (mounted) context.go('/otp');
      }
    } catch (error) {
      if (mounted) setState(() => _error = coreFlowError(error));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final title = widget.suspended ? 'Account suspended' : 'Code expired';
    return CoreFlowPage(
      title: title,
      onBack: () => context.go('/sign-in'),
      children: [
        const SizedBox(height: 20),
        Center(
          child: Container(
            width: 76,
            height: 76,
            decoration: BoxDecoration(
              color: widget.suspended
                  ? const Color(0xFFFFEFF4)
                  : const Color(0xFFFFF2DD),
              borderRadius: BorderRadius.circular(25),
            ),
            child: Icon(
              widget.suspended
                  ? Icons.close_rounded
                  : Icons.priority_high_rounded,
              size: 34,
              color: widget.suspended
                  ? const Color(0xFFEC174D)
                  : const Color(0xFFD97B00),
            ),
          ),
        ),
        const SizedBox(height: 16),
        Text(
          title,
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: 23, fontWeight: FontWeight.w800),
        ),
        const SizedBox(height: 6),
        Text(
          widget.suspended
              ? 'This account cannot sign in right now. Contact Sahajomy support for assistance.'
              : 'This verification code is no longer valid. Request a new code to continue securely.',
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: 13, height: 1.4, color: coreMuted),
        ),
        const SizedBox(height: 16),
        if (_error != null) CoreError(_error!),
        FilledButton(
          onPressed: _busy ? null : _continue,
          child: Text(
            _busy
                ? 'Please wait…'
                : widget.suspended
                ? 'Contact support'
                : 'Request new code',
          ),
        ),
        TextButton(
          onPressed: _busy ? null : () => context.go('/sign-in'),
          child: const Text('Return to sign in'),
        ),
      ],
    );
  }
}
