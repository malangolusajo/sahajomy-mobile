import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/auth/session.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/providers.dart';
import '../../../core/security/app_link_guard.dart';
import '../../../core/ui/core_flow_ui.dart';
import '../../auth/data/auth_repository.dart';
import '../data/workspace_repository.dart';

class CheckingWorkspacePage extends ConsumerStatefulWidget {
  const CheckingWorkspacePage({super.key});
  @override
  ConsumerState<CheckingWorkspacePage> createState() =>
      _CheckingWorkspacePageState();
}

class _CheckingWorkspacePageState extends ConsumerState<CheckingWorkspacePage> {
  String? _error;
  bool _busy = false;
  @override
  void initState() {
    super.initState();
    _check();
  }

  Future<void> _check() async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final store = ref.read(sessionStoreProvider);
      final session = await store.read();
      if (session == null) {
        if (mounted) context.go('/sign-in');
        return;
      }
      final verified = await ref
          .read(authRepositoryProvider)
          .verifyStoredSession(session);
      if (!mounted) return;
      await store.save(verified);
      final notifier = ref.read(workspaceProvider.notifier);
      await notifier.ready;
      final previous = ref.read(workspaceProvider);
      final repository = ref.read(workspaceRepositoryProvider);
      final memberships = await repository.list();
      if (!mounted) return;
      if (previous.hasCompany) {
        final membership = memberships
            .where((w) => w.companyId == previous.companyId)
            .firstOrNull;
        if (membership == null) {
          await notifier.clearWorkspace();
          if (mounted) context.go('/account/workspaces');
          return;
        }
        await notifier.setWorkspace(
          companyId: membership.companyId!,
          companyName: membership.name,
          branchId: previous.branchId ?? membership.branchId,
          branchName: previous.branchName ?? membership.branchName,
          role: membership.role,
          permissions: membership.permissions,
        );
        await repository.verifyContext();
      }
      if (!mounted) return;
      final destination = sanitizePendingDestination(
        ref.read(pendingDestinationProvider),
        role: verified.role,
      );
      ref.read(pendingDestinationProvider.notifier).state = null;
      context.go(
        destination != null && notifier.canOpenRoute(destination)
            ? destination
            : homeForRole(verified.role),
      );
    } on ApiException catch (error) {
      if (!mounted) return;
      if (error.isUnauthorized ||
          error.message.toLowerCase().contains('account suspended')) {
        await ref.read(workspaceProvider.notifier).clearWorkspace();
        await ref.read(sessionStoreProvider).clear();
        if (mounted) {
          context.go(
            error.message.toLowerCase().contains('suspended')
                ? '/account-suspended'
                : '/sign-in',
          );
        }
      } else {
        setState(() => _error = coreFlowError(error));
      }
    } catch (error) {
      if (mounted) setState(() => _error = coreFlowError(error));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => CoreFlowPage(
    title: 'Checking your workspace',
    canGoBack: true,
    onBack: () => context.go('/account/workspaces'),
    children: [
      const SizedBox(height: 118),
      Center(
        child: Container(
          width: 76,
          height: 76,
          decoration: BoxDecoration(
            color: const Color(0xFFFFF2DD),
            borderRadius: BorderRadius.circular(25),
          ),
          child: const Icon(
            Icons.more_horiz,
            color: Color(0xFFD97B00),
            size: 36,
          ),
        ),
      ),
      const SizedBox(height: 16),
      const Text(
        'Checking your workspace',
        textAlign: TextAlign.center,
        style: TextStyle(fontSize: 23, fontWeight: FontWeight.w800),
      ),
      const SizedBox(height: 6),
      const Text(
        'Confirming your identity, role and branch before loading protected data.',
        textAlign: TextAlign.center,
        style: TextStyle(color: coreMuted, fontSize: 13, height: 1.4),
      ),
      const SizedBox(height: 16),
      if (_busy)
        const LinearProgressIndicator(
          color: coreCoral,
          backgroundColor: coreBorder,
          minHeight: 8,
          borderRadius: BorderRadius.all(Radius.circular(8)),
          semanticsLabel: 'Verifying workspace',
        ),
      if (_error != null) ...[
        CoreError(_error!),
        FilledButton(
          onPressed: _busy ? null : _check,
          child: const Text('Try again'),
        ),
        TextButton(
          onPressed: () => context.go('/account/workspaces'),
          child: const Text('Choose another workspace'),
        ),
      ],
    ],
  );
}

String homeForRole(UserRole role) => switch (role) {
  UserRole.customer => '/customer',
  UserRole.cargoAdmin => '/cargo-admin',
  UserRole.sourcingAgent => '/sourcing-agent',
  UserRole.superAdmin => '/super-admin',
};
