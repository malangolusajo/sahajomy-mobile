import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../presentation/customer_components.dart';

class HelpSupportPage extends StatelessWidget {
  const HelpSupportPage({super.key});

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Help & support',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        const CustomerHeroCard(
          eyebrow: 'Account',
          title: 'Your account',
          subtitle: 'Profile, workspace, privacy and support settings stay in one predictable place.',
        ),
        const SizedBox(height: 24),
        Container(
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: appBorder),
          ),
          child: Column(
            children: [
              _menuRow(Icons.person_outline, 'Profile', 'Name, phone and profile image', brandCoral, () => context.push('/customer/profile')),
              const Divider(height: 1, indent: 56),
              _menuRow(Icons.workspaces_outline, 'Workspace & role', 'Customer · Personal', appMuted, null),
              const Divider(height: 1, indent: 56),
              _menuRow(Icons.lock_outline, 'Privacy & security', 'Sessions and secure data', appMuted, () => context.push('/customer/privacy')),
              const Divider(height: 1, indent: 56),
              _menuRow(Icons.help_outline, 'Help & support', 'Contact Sahajomy', appMuted, null),
            ],
          ),
        ),
      ],
    ),
  );

  Widget _menuRow(IconData icon, String title, String subtitle, Color iconColor, VoidCallback? onTap) => ListTile(
    leading: Icon(icon, color: iconColor),
    title: Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
    subtitle: Text(subtitle, style: const TextStyle(color: appMuted, fontSize: 13)),
    trailing: const Icon(Icons.chevron_right, color: appMuted),
    onTap: onTap,
  );
}
