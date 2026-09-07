import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/auth/session_store.dart';
import '../../../../core/providers.dart';
import '../../../auth/data/auth_repository.dart';

class CustomerMorePage extends ConsumerStatefulWidget {
  const CustomerMorePage({super.key});

  @override
  ConsumerState<CustomerMorePage> createState() => _CustomerMorePageState();
}

class _CustomerMorePageState extends ConsumerState<CustomerMorePage> {
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
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(20),
    children: [
      Text(
        'Customer operations',
        style: Theme.of(context).textTheme.titleLarge,
      ),
      const SizedBox(height: 6),
      const Text('Manage your cargo activity and delivery details.'),
      const SizedBox(height: 20),
      _MenuItem(
        icon: Icons.event_available_outlined,
        title: 'Bookings',
        subtitle: 'View your container-space bookings.',
        onTap: () => context.push('/customer/bookings'),
      ),
      _MenuItem(
        icon: Icons.inventory_2_outlined,
        title: 'Available containers',
        subtitle: 'Browse active container options.',
        onTap: () => context.push('/customer/containers'),
      ),
      _MenuItem(
        icon: Icons.directions_boat_outlined,
        title: 'Sea bookings',
        subtitle: 'Review sea bookings, payments, and documents.',
        onTap: () => context.push('/customer/sea-bookings'),
      ),
      _MenuItem(
        icon: Icons.flight_outlined,
        title: 'Express Air Cargo',
        subtitle: 'Create and track air cargo bookings.',
        onTap: () => context.push('/customer/express-air-cargo'),
      ),
      _MenuItem(
        icon: Icons.location_on_outlined,
        title: 'China addresses',
        subtitle: 'Copy your forwarding address and shipping mark.',
        onTap: () => context.push('/customer/china-addresses'),
      ),
      _MenuItem(
        icon: Icons.description_outlined,
        title: 'Shipping documents',
        subtitle: 'View invoices, receipts, and packing lists.',
        onTap: () => context.push('/customer/documents'),
      ),
      const SizedBox(height: 24),
      Text('Account', style: Theme.of(context).textTheme.titleLarge),
      const SizedBox(height: 8),
      _MenuItem(
        icon: Icons.person_outline,
        title: 'My profile',
        subtitle: 'View your verified account details.',
        onTap: () => context.push('/customer/profile'),
      ),
      _MenuItem(
        icon: Icons.swap_horiz_rounded,
        title: 'Switch workspace',
        subtitle: 'Change company or branch context securely.',
        onTap: () => context.push('/account/workspaces'),
      ),
      _MenuItem(
        icon: Icons.logout_rounded,
        title: _isSigningOut ? 'Signing out...' : 'Sign out',
        subtitle: 'Remove your secure session from this device.',
        onTap: _isSigningOut ? null : _signOut,
      ),
    ],
  );
}

class _MenuItem extends StatelessWidget {
  const _MenuItem({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Card(
    child: ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      leading: Icon(icon, color: Theme.of(context).colorScheme.primary),
      title: Text(title, style: const TextStyle(fontWeight: FontWeight.w800)),
      subtitle: Text(subtitle),
      trailing: const Icon(Icons.chevron_right),
      onTap: onTap,
    ),
  );
}
