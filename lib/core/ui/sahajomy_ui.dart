import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../../app/theme.dart';

class SahajomyBrandMark extends StatelessWidget {
  const SahajomyBrandMark({super.key, this.size = 64, this.showShadow = true});

  final double size;
  final bool showShadow;

  @override
  Widget build(BuildContext context) => Semantics(
    image: true,
    label: 'Sahajomy',
    child: Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(size * .29),
        boxShadow: showShadow
            ? [
                BoxShadow(
                  color: brandNavy.withValues(alpha: .18),
                  blurRadius: size * .32,
                  offset: Offset(0, size * .12),
                ),
              ]
            : null,
      ),
      child: SvgPicture.asset('assets/branding/sahajomy-logo.svg'),
    ),
  );
}

class SahajomyWordmark extends StatelessWidget {
  const SahajomyWordmark({super.key, this.light = false, this.markSize = 38});

  final bool light;
  final double markSize;

  @override
  Widget build(BuildContext context) => SahajomyBrandMark(size: markSize, showShadow: false);
}

class SahajomyScreenHeader extends StatelessWidget
    implements PreferredSizeWidget {
  const SahajomyScreenHeader({
    required this.title,
    super.key,
    this.role,
    this.showBack = true,
    this.onNotificationTap,
    this.actions,
  });

  final String? role;
  final String title;
  final bool showBack;
  final VoidCallback? onNotificationTap;
  final List<Widget>? actions;

  @override
  Size get preferredSize => const Size.fromHeight(64);

  @override
  Widget build(BuildContext context) => AppBar(
    automaticallyImplyLeading: false,
    leading: showBack && Navigator.of(context).canPop()
        ? IconButton(
            onPressed: () => Navigator.maybePop(context),
            icon: const Icon(Icons.chevron_left_rounded, size: 30),
            tooltip: 'Back',
          )
        : null,
    title: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (_professionalRoleLabel(role) case final roleLabel?) ...[
          Text(
            roleLabel,
            style: const TextStyle(
              color: brandCoral,
              fontSize: 10,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.25,
            ),
          ),
          const SizedBox(height: 1),
        ],
        Text(
          title,
          style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800),
        ),
      ],
    ),
    centerTitle: false,
    actions: actions ??
        (onNotificationTap == null
            ? null
            : [
                IconButton(
                  tooltip: 'Notifications',
                  onPressed: onNotificationTap,
                  icon: const Icon(Icons.notifications_none_rounded),
                ),
              ]),
  );
}

class SahajomyWorkspaceHeader extends StatelessWidget
    implements PreferredSizeWidget {
  const SahajomyWorkspaceHeader({
    required this.title,
    super.key,
    this.role,
    this.onNotificationTap,
  });

  final String? role;
  final String title;
  final VoidCallback? onNotificationTap;

  @override
  Size get preferredSize => const Size.fromHeight(64);

  @override
  Widget build(BuildContext context) => AppBar(
    title: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (_professionalRoleLabel(role) case final roleLabel?) ...[
          Text(
            roleLabel,
            style: const TextStyle(
              color: brandCoral,
              fontSize: 10,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.25,
            ),
          ),
          const SizedBox(height: 1),
        ],
        Text(
          title,
          style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w800),
        ),
      ],
    ),
    centerTitle: false,
    actions: onNotificationTap == null
        ? null
        : [
            IconButton(
              tooltip: 'Notifications',
              onPressed: onNotificationTap,
              icon: const Icon(Icons.notifications_none_rounded),
            ),
          ],
  );
}

String? _professionalRoleLabel(String? role) => switch (role) {
  null || '' => null,
  'Customer' => 'MY ACCOUNT',
  'Public' || 'Shared' => 'SAHAJOMY',
  'Cargo Admin' => 'CARGO OPERATIONS',
  'Sourcing Agent' => 'SOURCING WORKSPACE',
  'Super Admin' => 'PLATFORM ADMIN',
  _ => role.toUpperCase(),
};

class SahajomyPreviewNavigation extends StatelessWidget {
  const SahajomyPreviewNavigation({
    required this.selectedIndex,
    required this.onSelected,
    required this.destinations,
    super.key,
  });

  final int selectedIndex;
  final ValueChanged<int> onSelected;
  final List<SahajomyNavigationDestination> destinations;

  @override
  Widget build(BuildContext context) => NavigationBar(
    selectedIndex: selectedIndex,
    onDestinationSelected: onSelected,
    destinations: [for (final destination in destinations)
      NavigationDestination(icon: Icon(destination.icon), label: destination.label),
    ],
  );
}

class SahajomyNavigationDestination {
  const SahajomyNavigationDestination({
    required this.label,
    required this.icon,
  });

  final String label;
  final IconData icon;
}

class SahajomyPreviewRow extends StatelessWidget {
  const SahajomyPreviewRow({
    required this.title,
    required this.subtitle,
    required this.icon,
    super.key,
    this.trailing,
    this.onTap,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final Widget? trailing;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Material(
    color: Colors.white,
    child: InkWell(
      onTap: onTap,
      child: Container(
        constraints: const BoxConstraints(minHeight: 72),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        decoration: const BoxDecoration(
          border: Border(bottom: BorderSide(color: Color(0xFFE2E8F0))),
        ),
        child: Row(
          children: [
            Container(
              width: 30,
              height: 30,
              alignment: Alignment.center,
              color: const Color(0xFFFFF2EE),
              child: Icon(icon, size: 16, color: const Color(0xFFE85A3A)),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    subtitle,
                    style: const TextStyle(
                      fontSize: 12,
                      height: 1.35,
                      color: Color(0xFF64748B),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            trailing ??
                const Icon(
                  Icons.chevron_right_rounded,
                  color: Color(0xFF94A3B8),
                ),
          ],
        ),
      ),
    ),
  );
}

class SahajomyStatusPill extends StatelessWidget {
  const SahajomyStatusPill({required this.label, super.key});

  final String label;

  @override
  Widget build(BuildContext context) {
    final status = label.trim().toLowerCase().replaceAll(' ', '_');
    final color = switch (status) {
      'paid' || 'completed' || 'collected' || 'delivered' || 'active' || 'approved' => const Color(0xFF08705F),
      'pending' || 'nearly_full' || 'awaiting_payment' || 'on_hold' => const Color(0xFF8F5308),
      'cancelled' || 'rejected' || 'failed' || 'expired' || 'overdue' => appError,
      _ => brandNavy,
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(color: color.withValues(alpha: .09), borderRadius: BorderRadius.circular(999)),
      child: Text(sahajomyTitleCase(label), style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w700)),
    );
  }
}

class SahajomySectionCard extends StatelessWidget {
  const SahajomySectionCard({
    required this.title,
    required this.children,
    super.key,
    this.subtitle,
  });

  final String title;
  final String? subtitle;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          if (subtitle != null) ...[
            const SizedBox(height: 4),
            Text(subtitle!, style: Theme.of(context).textTheme.bodyMedium),
          ],
          const SizedBox(height: 12),
          ...children,
        ],
      ),
    ),
  );
}

class SahajomyMetricTile extends StatelessWidget {
  const SahajomyMetricTile({
    required this.label,
    required this.value,
    super.key,
    this.width = 164,
  });

  final String label;
  final Object? value;
  final double width;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: width,
    child: Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              sahajomyDisplayValue(value),
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 4),
            Text(label, style: Theme.of(context).textTheme.bodyMedium),
          ],
        ),
      ),
    ),
  );
}

class SahajomyMessageState extends StatelessWidget {
  const SahajomyMessageState({
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
          Icon(icon, size: 44, color: brandNavy),
          const SizedBox(height: 14),
          Text(message, textAlign: TextAlign.center),
          if (onAction != null && actionLabel != null) ...[
            const SizedBox(height: 16),
            OutlinedButton(onPressed: onAction, child: Text(actionLabel!)),
          ],
        ],
      ),
    ),
  );
}

class SahajomyKeyValueList extends StatelessWidget {
  const SahajomyKeyValueList({required this.entries, super.key});

  final Map<String, Object?> entries;

  @override
  Widget build(BuildContext context) => Column(
    children: entries.entries
        .map(
          (entry) => Padding(
            padding: const EdgeInsets.symmetric(vertical: 5),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Text(
                    sahajomyTitleCase(entry.key),
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Text(
                    sahajomyDisplayValue(entry.value),
                    textAlign: TextAlign.right,
                    style: const TextStyle(
                      color: appInk,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
          ),
        )
        .toList(),
  );
}

String sahajomyTitleCase(String value) => value
    .split('_')
    .where((part) => part.isNotEmpty)
    .map(
      (part) =>
          '${part[0].toUpperCase()}${part.substring(1).replaceAll('-', ' ')}',
    )
    .join(' ');

String sahajomyDisplayValue(Object? value) {
  if (value == null) return 'Not available';
  if (value is bool) return value ? 'Yes' : 'No';
  if (value is num) return '$value';
  if (value is List) {
    if (value.isEmpty) return 'None';
    return value.map(sahajomyDisplayValue).join(', ');
  }
  if (value is Map) {
    if (value.isEmpty) return 'None';
    return value.entries
        .map(
          (entry) =>
              '${sahajomyTitleCase('${entry.key}')}: ${sahajomyDisplayValue(entry.value)}',
        )
        .join(' • ');
  }
  final text = value.toString().trim();
  return text.isEmpty ? 'Not available' : text;
}
