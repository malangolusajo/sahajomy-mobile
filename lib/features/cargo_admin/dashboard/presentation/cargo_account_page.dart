import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../../../core/providers.dart';
import '../../../customer/presentation/customer_components.dart';

class CargoAccountPage extends ConsumerWidget {
  const CargoAccountPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) => CustomerScaffold(
    eyebrow: 'CARGO COMPANY',
    title: 'Cargo · Account',
    notificationRoute: '/cargo/notifications',
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
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)),
          child: Column(
            children: [
              _row(context, Icons.person_outline, 'Profile', 'Name, phone and profile image', brandCoral, null),
              const Divider(height: 1, indent: 56),
              _row(context, Icons.workspaces_outline, 'Workspace & role', 'Cargo Company · Operator', appMuted, '/cargo/workspace/branch'),
              const Divider(height: 1, indent: 56),
              _row(context, Icons.warehouse_outlined, 'Warehouses', 'Manage your warehouse locations', appMuted, '/cargo/warehouses'),
              const Divider(height: 1, indent: 56),
              _row(context, Icons.groups_outlined, 'Staff & branches', 'Invite staff and assign branches', appMuted, '/cargo/staff'),
              const Divider(height: 1, indent: 56),
              _row(context, Icons.qr_code_scanner_outlined, 'Scanner', 'Scan intake labels', appMuted, '/cargo/scanner'),
              const Divider(height: 1, indent: 56),
              _row(context, Icons.assignment_outlined, 'Customs', 'Customs clearance', appMuted, '/cargo/customs'),
              const Divider(height: 1, indent: 56),
              _row(context, Icons.notifications_outlined, 'Notifications', 'Recent alerts', appMuted, '/cargo/notifications'),
              const Divider(height: 1, indent: 56),
              _row(context, Icons.lock_outline, 'Privacy & security', 'Sessions and secure data', appMuted, null),
              const Divider(height: 1, indent: 56),
              _row(context, Icons.help_outline, 'Help & support', 'Contact Sahajomy', appMuted, null),
            ],
          ),
        ),
        const SizedBox(height: 24),
        OutlinedButton.icon(
          onPressed: () async {
            await ref.read(sessionStoreProvider).clear();
            if (context.mounted) context.go('/sign-in');
          },
          icon: const Icon(Icons.logout),
          label: const Text('Sign out'),
        ),
      ],
    ),
  );

  Widget _row(BuildContext context, IconData icon, String title, String subtitle, Color iconColor, String? route) => ListTile(
    leading: Icon(icon, color: iconColor),
    title: Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
    subtitle: Text(subtitle, style: const TextStyle(color: appMuted, fontSize: 13)),
    trailing: const Icon(Icons.chevron_right, color: appMuted),
    onTap: route != null ? () => context.push(route) : null,
  );
}
