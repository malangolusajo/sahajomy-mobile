import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../network/api_exception.dart';

/// Visual tone for the status icon.
enum StatusTone { warning, error, success }

/// Maps backend error conditions to the approved status-screen designs.
class StatusPage extends StatelessWidget {
  const StatusPage({
    super.key,
    required this.title,
    required this.heading,
    required this.description,
    this.tone = StatusTone.warning,
    this.reference,
    this.referenceLabel,
    this.onContinue,
    this.continueLabel = 'Continue',
    this.onDetails,
    this.canGoBack = true,
  });

  /// AppBar title (e.g. "Loading data", "You are offline").
  final String title;

  /// Large heading below the icon.
  final String heading;

  /// Descriptive body text.
  final String description;

  /// Icon colour: warning (amber), error (red X), or success (green check).
  final StatusTone tone;

  /// Optional reference number shown in the card (e.g. "SAH-260907-4829").
  final String? reference;

  /// Label for the reference row (default "REF").
  final String? referenceLabel;

  /// Called when the primary Continue button is pressed.
  final VoidCallback? onContinue;

  /// Label on the Continue button.
  final String continueLabel;

  /// Called when the Details link in the reference card is pressed.
  final VoidCallback? onDetails;

  /// Whether the AppBar shows a back button.
  final bool canGoBack;

  /// Factory: create from an [ApiException] using the approved screen vocabulary.
  factory StatusPage.fromApiException({
    required ApiException error,
    VoidCallback? onContinue,
    VoidCallback? onDetails,
    String? reference,
    String? titleOverride,
  }) {
    final mapped = _exceptionMapping(error, titleOverride);
    return StatusPage(
      title: mapped.$1,
      heading: mapped.$2,
      description: mapped.$3,
      tone: mapped.$4,
      reference: reference,
      onContinue: onContinue ?? () {},
      onDetails: onDetails,
    );
  }

  static (String, String, String, StatusTone) _exceptionMapping(
    ApiException error,
    String? titleOverride,
  ) {
    if (error.isForbidden) {
      return (
        titleOverride ?? 'You cannot access this',
        'You cannot access this',
        'Your current role or workspace does not have permission for this screen.',
        StatusTone.error,
      );
    }
    if (error.isConflict) {
      return (
        titleOverride ?? 'Something changed',
        'Something changed',
        'The record was updated elsewhere. Refresh before trying again.',
        StatusTone.warning,
      );
    }
    if (error.isGone) {
      return (
        titleOverride ?? 'This request expired',
        'This request expired',
        'This action is no longer valid. Return and request a new one.',
        StatusTone.warning,
      );
    }
    if (error.isValidationError) {
      return (
        titleOverride ?? 'Check the highlighted details',
        'Check the highlighted details',
        'Some information needs attention before you can continue.',
        StatusTone.error,
      );
    }
    if (error.isRateLimited) {
      return (
        titleOverride ?? 'Too many attempts',
        'Too many attempts',
        'Please wait before trying again. This protects your account and platform services.',
        StatusTone.warning,
      );
    }
    if (error.isUnauthorized) {
      return (
        titleOverride ?? 'Session expired',
        'Session expired',
        'Your session is no longer active. Sign in again to continue.',
        StatusTone.warning,
      );
    }
    if (error.isServerError) {
      return (
        titleOverride ?? 'Something went wrong',
        'Something went wrong',
        'The server could not complete this request. Please try again shortly.',
        StatusTone.error,
      );
    }
    return (
      titleOverride ?? 'Something changed',
      'Something changed',
      error.message.isNotEmpty
          ? error.message
          : 'An unexpected issue occurred. Please try again.',
      StatusTone.warning,
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: Colors.white,
        surfaceTintColor: Colors.transparent,
        toolbarHeight: MediaQuery.textScalerOf(context).scale(20) > 26
            ? MediaQuery.textScalerOf(context).scale(20) * 2 + 24
            : 64,
        leadingWidth: canGoBack ? 64 : 20,
        leading: canGoBack
            ? Padding(
                padding: const EdgeInsets.only(left: 16, top: 8, bottom: 8),
                child: IconButton.outlined(
                  style: IconButton.styleFrom(
                    backgroundColor: Colors.white,
                    side: const BorderSide(color: appBorder),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14),
                    ),
                  ),
                  tooltip: 'Back',
                  icon: const Icon(Icons.chevron_left, color: brandNavy),
                  onPressed: () {
                    if (context.canPop()) {
                      context.pop();
                    } else {
                      context.go('/sign-in');
                    }
                  },
                ),
              )
            : null,
        title: Text(
          title,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.w800,
            color: appInk,
          ),
        ),
        centerTitle: false,
        bottom: const PreferredSize(
          preferredSize: Size.fromHeight(1),
          child: Divider(height: 1, color: appBorder),
        ),
      ),
      body: SafeArea(
        top: false,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
          padding: const EdgeInsets.fromLTRB(20, 24, 20, 32),
          children: [
            const SizedBox(height: 20),
            Center(child: _StatusIcon(tone: tone)),
            const SizedBox(height: 20),
            Text(
              heading,
              textAlign: TextAlign.center,
              style: theme.textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              description,
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyMedium,
            ),
            if (reference != null) ...[
              const SizedBox(height: 24),
              _ReferenceCard(
                reference: reference!,
                label: referenceLabel,
                onDetails: onDetails,
              ),
            ],
            const SizedBox(height: 24),
            FilledButton(
              onPressed: onContinue,
              child: Text(continueLabel),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatusIcon extends StatelessWidget {
  const _StatusIcon({required this.tone});
  final StatusTone tone;

  @override
  Widget build(BuildContext context) {
    final (Color bg, Color fg, IconData icon) = switch (tone) {
      StatusTone.warning => (
        const Color(0xFFFFF2DD),
        const Color(0xFFD97B00),
        Icons.warning_amber_rounded,
      ),
      StatusTone.error => (
        const Color(0xFFFFEFF4),
        const Color(0xFFEC174D),
        Icons.close_rounded,
      ),
      StatusTone.success => (
        const Color(0xFFE5F7F0),
        const Color(0xFF059669),
        Icons.check_rounded,
      ),
    };
    return Container(
      width: 76,
      height: 76,
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(25),
      ),
      child: Icon(icon, size: 34, color: fg),
    );
  }
}

class _ReferenceCard extends StatelessWidget {
  const _ReferenceCard({
    required this.reference,
    this.label,
    this.onDetails,
  });

  final String reference;
  final String? label;
  final VoidCallback? onDetails;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: appBorder),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(
              color: const Color(0xFFF5F7FA),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              label ?? 'REF',
              style: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w800,
                color: appInk,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  reference,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: appInk,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  'Reference saved to your account',
                  style: TextStyle(
                    fontSize: 11,
                    color: theme.textTheme.bodySmall?.color ?? appMuted,
                  ),
                ),
              ],
            ),
          ),
          if (onDetails != null)
            TextButton(
              onPressed: onDetails,
              style: TextButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                minimumSize: Size.zero,
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
              child: const Text(
                'Details',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: brandNavy,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// Convenience constructors for the 10 approved status screens.
class StatusScreens {
  StatusScreens._();

  /// Screen 1: Loading data
  static StatusPage loading({
    String? reference,
    VoidCallback? onContinue,
    VoidCallback? onDetails,
  }) =>
      StatusPage(
        title: 'Loading data',
        heading: 'Loading your data',
        description:
            'Keeping your current screen stable while fresh data arrives.',
        tone: StatusTone.warning,
        reference: reference,
        onContinue: onContinue,
        onDetails: onDetails,
      );

  /// Screen 2: Nothing here yet
  static StatusPage empty({
    String? reference,
    VoidCallback? onContinue,
    VoidCallback? onDetails,
  }) =>
      StatusPage(
        title: 'Nothing here yet',
        heading: 'Nothing here yet',
        description:
            'When records are available, they will appear here with the actions you need.',
        tone: StatusTone.warning,
        reference: reference,
        onContinue: onContinue,
        onDetails: onDetails,
      );

  /// Screen 3: You are offline
  static StatusPage offline({
    String? reference,
    VoidCallback? onContinue,
    VoidCallback? onDetails,
  }) =>
      StatusPage(
        title: 'You are offline',
        heading: 'You are offline',
        description:
            'You can still view cached information. Reconnect to refresh or make changes.',
        tone: StatusTone.warning,
        reference: reference,
        onContinue: onContinue,
        onDetails: onDetails,
      );

  /// Screen 4: You cannot access this
  static StatusPage forbidden({
    String? reference,
    VoidCallback? onContinue,
    VoidCallback? onDetails,
  }) =>
      StatusPage(
        title: 'You cannot access this',
        heading: 'You cannot access this',
        description:
            'Your current role or workspace does not have permission for this screen.',
        tone: StatusTone.error,
        reference: reference,
        onContinue: onContinue,
        onDetails: onDetails,
      );

  /// Screen 5: Something changed
  static StatusPage conflict({
    String? reference,
    VoidCallback? onContinue,
    VoidCallback? onDetails,
  }) =>
      StatusPage(
        title: 'Something changed',
        heading: 'Something changed',
        description:
            'The record was updated elsewhere. Refresh before trying again.',
        tone: StatusTone.warning,
        reference: reference,
        onContinue: onContinue,
        onDetails: onDetails,
      );

  /// Screen 6: This request expired
  static StatusPage expired({
    String? reference,
    VoidCallback? onContinue,
    VoidCallback? onDetails,
  }) =>
      StatusPage(
        title: 'This request expired',
        heading: 'This request expired',
        description:
            'This action is no longer valid. Return and request a new one.',
        tone: StatusTone.warning,
        reference: reference,
        onContinue: onContinue,
        onDetails: onDetails,
      );

  /// Screen 7: Check the highlighted details
  static StatusPage validationError({
    String? reference,
    VoidCallback? onContinue,
    VoidCallback? onDetails,
  }) =>
      StatusPage(
        title: 'Check the highlighted details',
        heading: 'Check the highlighted details',
        description:
            'Some information needs attention before you can continue.',
        tone: StatusTone.error,
        reference: reference,
        onContinue: onContinue,
        onDetails: onDetails,
      );

  /// Screen 8: Too many attempts
  static StatusPage rateLimited({
    String? reference,
    VoidCallback? onContinue,
    VoidCallback? onDetails,
  }) =>
      StatusPage(
        title: 'Too many attempts',
        heading: 'Too many attempts',
        description:
            'Please wait before trying again. This protects your account and platform services.',
        tone: StatusTone.warning,
        reference: reference,
        onContinue: onContinue,
        onDetails: onDetails,
      );

  /// Screen 9: Confirm this action
  static StatusPage confirm({
    String? reference,
    String? description,
    VoidCallback? onContinue,
    VoidCallback? onDetails,
  }) =>
      StatusPage(
        title: 'Confirm this action',
        heading: 'Confirm this action',
        description: description ??
            'Review the impact carefully before continuing.',
        tone: StatusTone.error,
        reference: reference,
        continueLabel: 'Confirm',
        onContinue: onContinue,
        onDetails: onDetails,
      );

  /// Screen 10: Action completed
  static StatusPage success({
    String? reference,
    String? description,
    VoidCallback? onContinue,
    VoidCallback? onDetails,
  }) =>
      StatusPage(
        title: 'Action completed',
        heading: 'Action completed',
        description: description ??
            'Your change was saved successfully and the latest data is now shown.',
        tone: StatusTone.success,
        reference: reference,
        onContinue: onContinue,
        onDetails: onDetails,
      );
}
