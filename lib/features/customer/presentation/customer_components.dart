import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';

/// Customer page scaffold with role-aware app bar (no "Sahajomy" title).
class CustomerScaffold extends StatelessWidget {
  const CustomerScaffold({
    required this.title,
    super.key,
    this.body,
    this.floatingActionButton,
    this.showBack = true,
    this.actions,
    this.bottomNavigationBar,
    this.backgroundColor,
    this.padding,
    this.eyebrow = 'CUSTOMER',
    this.notificationRoute = '/customer/notifications',
  });

  final String title;
  final Widget? body;
  final Widget? floatingActionButton;
  final bool showBack;
  final List<Widget>? actions;
  final Widget? bottomNavigationBar;
  final Color? backgroundColor;
  final EdgeInsets? padding;
  final String eyebrow;
  final String notificationRoute;

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: backgroundColor ?? appCanvas,
    appBar: AppBar(
      automaticallyImplyLeading: false,
      leading: showBack && Navigator.of(context).canPop()
          ? IconButton(
              onPressed: () => Navigator.of(context).maybePop(),
              icon: const Icon(Icons.chevron_left_rounded, size: 30),
              tooltip: 'Back',
            )
          : null,
      title: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            eyebrow,
            style: const TextStyle(
              color: brandCoral,
              fontSize: 10,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.25,
              height: 1.2,
            ),
          ),
          const SizedBox(height: 1),
          Text(
            title,
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w800,
              color: appInk,
              height: 1.2,
            ),
          ),
        ],
      ),
      centerTitle: false,
      actions: actions ??
          [
            IconButton(
              tooltip: 'Notifications',
              onPressed: () => context.push(notificationRoute),
              icon: Stack(
                clipBehavior: Clip.none,
                children: [
                  const Icon(Icons.notifications_none_rounded, size: 24),
                  Positioned(
                    right: 1,
                    top: 1,
                    child: Container(
                      width: 8,
                      height: 8,
                      decoration: const BoxDecoration(
                        color: brandCoral,
                        shape: BoxShape.circle,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 4),
          ],
    ),
    body: padding == null
        ? body
        : Padding(padding: padding!, child: body),
    floatingActionButton: floatingActionButton,
    bottomNavigationBar: bottomNavigationBar,
  );
}

/// Navy hero card with eyebrow, title, subtitle and coral accent line.
class CustomerHeroCard extends StatelessWidget {
  const CustomerHeroCard({
    required this.title,
    required this.subtitle,
    super.key,
    this.eyebrow,
    this.showAccent = true,
  });

  final String title;
  final String subtitle;
  final String? eyebrow;
  final bool showAccent;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(24),
    decoration: BoxDecoration(
      color: brandNavyDark,
      borderRadius: BorderRadius.circular(20),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (eyebrow != null)
          Text(
            eyebrow!.toUpperCase(),
            style: const TextStyle(
              color: Color(0xFFFFB89E),
              fontSize: 11,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.4,
            ),
          ),
        if (eyebrow != null) const SizedBox(height: 10),
        Text(
          title,
          style: const TextStyle(
            fontSize: 28,
            fontWeight: FontWeight.w900,
            color: Colors.white,
            height: 1.15,
          ),
        ),
        const SizedBox(height: 10),
        Text(
          subtitle,
          style: const TextStyle(
            color: Color(0xFFD1DEE6),
            fontSize: 14,
            height: 1.45,
          ),
        ),
        if (showAccent) ...[
          const SizedBox(height: 16),
          Container(
            width: 44,
            height: 4,
            decoration: BoxDecoration(
              color: brandCoral,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
        ],
      ],
    ),
  );
}

/// Operational list row used across customer screens.
class CustomerListItem extends StatelessWidget {
  const CustomerListItem({
    required this.badgeLabel,
    required this.title,
    required this.subtitle,
    super.key,
    this.badgeColor = brandCoral,
    this.status,
    this.statusColor,
    this.onTap,
    this.trailing,
    this.showChevron = true,
  });

  final String badgeLabel;
  final String title;
  final String subtitle;
  final Color badgeColor;
  final String? status;
  final Color? statusColor;
  final VoidCallback? onTap;
  final Widget? trailing;
  final bool showChevron;

  @override
  Widget build(BuildContext context) => Material(
    color: Colors.white,
    borderRadius: BorderRadius.circular(16),
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: appBorder, width: 1),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Container(
              width: 40,
              height: 40,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: badgeColor.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                badgeLabel,
                style: TextStyle(
                  color: badgeColor,
                  fontSize: 12,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w800,
                      color: appInk,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 3),
                  Text(
                    subtitle,
                    style: const TextStyle(
                      fontSize: 12.5,
                      color: appMuted,
                      height: 1.35,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
            const SizedBox(width: 10),
            if (status != null)
              CustomerStatusPill(
                label: status!,
                color: statusColor,
              ),
            if (status == null && trailing != null) trailing!,
            if (showChevron && trailing == null && status == null)
              const Icon(Icons.chevron_right_rounded, color: appMuted, size: 20),
          ],
        ),
      ),
    ),
  );
}

/// Status pill badge.
class CustomerStatusPill extends StatelessWidget {
  const CustomerStatusPill({
    required this.label,
    super.key,
    this.color,
  });

  final String label;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final c = color ?? _statusColor(label);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: c.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: c,
          fontSize: 11,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }

  static Color _statusColor(String label) {
    final l = label.trim().toLowerCase();
    if (l.contains('transit') || l.contains('departed') || l.contains('processing')) {
      return const Color(0xFF0891B2);
    }
    if (l.contains('paid') || l.contains('ready') || l.contains('delivered') ||
        l.contains('collected') || l.contains('confirmed') || l.contains('approved') ||
        l.contains('matched') || l.contains('available') || l.contains('success')) {
      return appSuccess;
    }
    if (l.contains('payment') || l.contains('pending') || l.contains('unpaid') ||
        l.contains('awaiting') || l.contains('expired') || l.contains('expiring')) {
      return appWarning;
    }
    if (l.contains('cancel') || l.contains('reject') || l.contains('fail') ||
        l.contains('expired') || l.contains('overdue')) {
      return appError;
    }
    return brandNavy;
  }
}

/// Quick action circular button with label.
class CustomerQuickAction extends StatelessWidget {
  const CustomerQuickAction({
    required this.label,
    required this.icon,
    super.key,
    this.color = brandCoral,
    this.onTap,
  });

  final String label;
  final Widget icon;
  final Color color;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
    onTap: onTap,
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 56,
          height: 56,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
          ),
          child: icon,
        ),
        const SizedBox(height: 8),
        Text(
          label,
          style: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w700,
            color: appInk,
          ),
          textAlign: TextAlign.center,
        ),
      ],
    ),
  );
}

/// Section header with optional "View all" link.
class CustomerSectionHeader extends StatelessWidget {
  const CustomerSectionHeader({
    required this.title,
    super.key,
    this.actionLabel,
    this.onAction,
  });

  final String title;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) => Row(
    mainAxisAlignment: MainAxisAlignment.spaceBetween,
    children: [
      Text(
        title,
        style: const TextStyle(
          fontSize: 18,
          fontWeight: FontWeight.w800,
          color: appInk,
        ),
      ),
      if (actionLabel != null)
        TextButton(
          onPressed: onAction,
          style: TextButton.styleFrom(
            padding: EdgeInsets.zero,
            foregroundColor: brandNavy,
            textStyle: const TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w700,
            ),
          ),
          child: Text(actionLabel!),
        ),
    ],
  );
}

/// Empty state widget.
class CustomerEmptyState extends StatelessWidget {
  const CustomerEmptyState({
    required this.icon,
    required this.message,
    super.key,
    this.actionLabel,
    this.onAction,
  });

  final IconData icon;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(
              color: brandCoralLight,
              shape: BoxShape.circle,
            ),
            child: Icon(icon, size: 30, color: brandCoral),
          ),
          const SizedBox(height: 16),
          Text(
            message,
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 15, color: appMuted),
          ),
          if (onAction != null && actionLabel != null) ...[
            const SizedBox(height: 18),
            FilledButton(onPressed: onAction, child: Text(actionLabel!)),
          ],
        ],
      ),
    ),
  );
}

/// Loading skeleton list.
class CustomerSkeletonList extends StatelessWidget {
  const CustomerSkeletonList({super.key, this.count = 3});

  final int count;

  @override
  Widget build(BuildContext context) => Column(
    children: List.generate(count, (i) => Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Container(
        height: 72,
        decoration: BoxDecoration(
          color: appBorder.withValues(alpha: 0.4),
          borderRadius: BorderRadius.circular(16),
        ),
      ),
    )),
  );
}
