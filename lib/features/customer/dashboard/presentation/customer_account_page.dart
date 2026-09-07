import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../../../core/auth/session_store.dart';
import '../../../../core/providers.dart';
import '../../../auth/data/auth_repository.dart';
import '../../presentation/customer_components.dart';

class CustomerAccountPage extends ConsumerStatefulWidget {
  const CustomerAccountPage({super.key});

  @override
  ConsumerState<CustomerAccountPage> createState() => _CustomerAccountPageState();
}

class _CustomerAccountPageState extends ConsumerState<CustomerAccountPage> {
  SessionStore get _store => ref.read(sessionStoreProvider);
  AuthRepository get _auth => ref.read(authRepositoryProvider);
  var _isSigningOut = false;

  Future<void> _signOut() async {
    setState(() => _isSigningOut = true);
    final session = await _store.read();
    try {
      if (session != null) await _auth.logout(session);
    } catch (_) {
      // Clearing the local encrypted session still protects this device offline.
    } finally {
      await ref.read(workspaceProvider.notifier).clearWorkspace();
      await _store.clear();
      ref.read(pendingDestinationProvider.notifier).state = null;
      ref.read(pendingPhoneNumberProvider.notifier).state = null;
      ref.read(pendingMfaChallengeProvider.notifier).state = null;
      ref.invalidate(apiClientProvider);
      if (mounted) {
        context.go('/sign-in');
      }
    }
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Account',
    showBack: false,
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
      children: [
        const CustomerHeroCard(
          eyebrow: 'Account',
          title: 'Your account',
          subtitle: 'Profile, workspace, privacy and support settings stay in one predictable place.',
        ),
        const SizedBox(height: 24),
        _AccountItem(
          badge: 'PF',
          badgeColor: brandCoral,
          title: 'Profile',
          subtitle: 'Name, phone and profile image',
          onTap: () => context.push('/customer/profile'),
        ),
        const SizedBox(height: 12),
        _AccountItem(
          badge: 'WS',
          badgeColor: brandNavy,
          title: 'Workspace & role',
          subtitle: 'Customer · Personal',
          onTap: () => context.push('/account/workspaces'),
        ),
        const SizedBox(height: 12),
        _AccountItem(
          badge: 'PV',
          badgeColor: brandNavy,
          title: 'Privacy & security',
          subtitle: 'Sessions and secure data',
          onTap: () => context.push('/customer/privacy'),
        ),
        const SizedBox(height: 12),
        _AccountItem(
          badge: 'HP',
          badgeColor: brandNavy,
          title: 'Help & support',
          subtitle: 'Contact Sahajomy',
          onTap: () => context.push('/customer/support'),
        ),
        const SizedBox(height: 28),
        OutlinedButton(
          onPressed: _isSigningOut ? null : _signOut,
          style: OutlinedButton.styleFrom(
            foregroundColor: appInk,
            side: const BorderSide(color: appBorder, width: 1.5),
            minimumSize: const Size.fromHeight(54),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
          ),
          child: Text(_isSigningOut ? 'Signing out...' : 'Sign out'),
        ),
      ],
    ),
  );
}

class _AccountItem extends StatelessWidget {
  const _AccountItem({
    required this.badge,
    required this.badgeColor,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final String badge;
  final Color badgeColor;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => CustomerListItem(
    badgeLabel: badge,
    badgeColor: badgeColor,
    title: title,
    subtitle: subtitle,
    onTap: onTap,
  );
}
