import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../../app/theme.dart';

class SahajomyBrandMark extends StatelessWidget {
  const SahajomyBrandMark({super.key, this.size = 64});

  final double size;

  @override
  Widget build(BuildContext context) => Container(
    width: size,
    height: size,
    padding: EdgeInsets.all(size * .12),
    decoration: BoxDecoration(
      color: brandNavy,
      borderRadius: BorderRadius.circular(size * .36),
    ),
    child: SvgPicture.asset('assets/branding/sahajomy-logo.svg'),
  );
}

class SahajomyScreenHeader extends StatelessWidget
    implements PreferredSizeWidget {
  const SahajomyScreenHeader({
    required this.role,
    required this.title,
    super.key,
    this.showBack = true,
    this.onNotificationTap,
  });

  final String role;
  final String title;
  final bool showBack;
  final VoidCallback? onNotificationTap;

  @override
  Size get preferredSize => const Size.fromHeight(64);

  @override
  Widget build(BuildContext context) => AppBar(
    automaticallyImplyLeading: false,
    leading: showBack
        ? IconButton(
            onPressed: () => Navigator.maybePop(context),
            icon: const Icon(Icons.chevron_left_rounded, size: 30),
            tooltip: 'Back',
          )
        : null,
    title: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          role.toUpperCase(),
          style: const TextStyle(
            color: brandCoral,
            fontSize: 10,
            fontWeight: FontWeight.w800,
            letterSpacing: 1.4,
          ),
        ),
        Text(
          title,
          style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800),
        ),
      ],
    ),
    centerTitle: true,
    actions: [
      IconButton(
        tooltip: 'Notifications',
        onPressed: onNotificationTap,
        icon: const Badge(child: Icon(Icons.notifications_none_rounded)),
      ),
    ],
  );
}

class SahajomyStatusPill extends StatelessWidget {
  const SahajomyStatusPill({required this.label, super.key});

  final String label;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
    decoration: BoxDecoration(
      color: const Color(0xFFFFEEE9),
      borderRadius: BorderRadius.circular(999),
    ),
    child: Text(
      label,
      style: const TextStyle(
        color: Color(0xFFE85A3A),
        fontSize: 10,
        fontWeight: FontWeight.w800,
      ),
      ),
    );
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
        .map((entry) => '${sahajomyTitleCase('${entry.key}')}: ${sahajomyDisplayValue(entry.value)}')
        .join(' • ');
  }
  final text = value.toString().trim();
  return text.isEmpty ? 'Not available' : text;
}
