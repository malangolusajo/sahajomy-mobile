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
