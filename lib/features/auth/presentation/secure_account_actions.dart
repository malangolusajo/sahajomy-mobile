import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/providers.dart';
import '../data/auth_repository.dart';

class SecureAccountActions extends ConsumerStatefulWidget {
  const SecureAccountActions({super.key});

  @override
  ConsumerState<SecureAccountActions> createState() =>
      _SecureAccountActionsState();
}

class _SecureAccountActionsState extends ConsumerState<SecureAccountActions> {
  bool _signingOut = false;

  Future<void> _signOut() async {
    if (_signingOut) return;
    setState(() => _signingOut = true);
    final store = ref.read(sessionStoreProvider);
    final session = await store.read();
    try {
      if (session != null) {
        await ref.read(authRepositoryProvider).logout(session);
      }
    } catch (_) {
      // Local teardown must still complete if revocation is unavailable.
    } finally {
      await ref.read(workspaceProvider.notifier).clearWorkspace();
      await store.clear();
      ref.read(pendingDestinationProvider.notifier).state = null;
      ref.read(pendingPhoneNumberProvider.notifier).state = null;
      ref.read(pendingMfaChallengeProvider.notifier).state = null;
      ref.invalidate(apiClientProvider);
      if (mounted) context.go('/sign-in');
    }
  }

  @override
  Widget build(BuildContext context) => Column(
    children: [
      Card(
        child: ListTile(
          leading: const Icon(Icons.swap_horiz_rounded),
          title: const Text(
            'Switch workspace',
            style: TextStyle(fontWeight: FontWeight.w800),
          ),
          subtitle: const Text('Change company or branch securely.'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: _signingOut ? null : () => context.push('/account/workspaces'),
        ),
      ),
      Card(
        child: ListTile(
          leading: const Icon(Icons.logout_rounded),
          title: Text(
            _signingOut ? 'Signing out…' : 'Sign out',
            style: const TextStyle(fontWeight: FontWeight.w800),
          ),
          subtitle: const Text('Remove this account and tenant data.'),
          onTap: _signingOut ? null : _signOut,
        ),
      ),
    ],
  );
}
