import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/providers.dart';
import '../../../core/ui/core_flow_ui.dart';
import '../data/workspace_repository.dart';

class BranchSelectionPage extends ConsumerStatefulWidget {
  const BranchSelectionPage({super.key});
  @override
  ConsumerState<BranchSelectionPage> createState() =>
      _BranchSelectionPageState();
}

class _BranchSelectionPageState extends ConsumerState<BranchSelectionPage> {
  late Future<List<WorkspaceBranch>> _future;
  Workspace? _workspace;
  WorkspaceBranch? _selected;
  bool _busy = false;
  String? _error;
  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<WorkspaceBranch>> _load() async {
    final repository = ref.read(workspaceRepositoryProvider);
    await ref.read(workspaceProvider.notifier).ready;
    final current = ref.read(workspaceProvider);
    final workspaces = await repository.list();
    final workspace = workspaces
        .where((w) => w.companyId != null && w.companyId == current.companyId)
        .firstOrNull;
    if (workspace == null) {
      throw const FormatException(
        'Select an available company workspace first.',
      );
    }
    _workspace = workspace;
    if (!workspace.permissions.contains('company.branch.manage')) {
      return workspace.branchId == null
          ? const []
          : [
              WorkspaceBranch(
                id: workspace.branchId!,
                name: workspace.branchName ?? 'Assigned branch',
                location: 'Assigned to your membership',
              ),
            ];
    }
    return repository.branches(workspace);
  }

  Future<void> _refresh() async {
    setState(() {
      _selected = null;
      _future = _load();
    });
    try {
      await _future;
    } catch (_) {
      /* Render error below. */
    }
  }

  Future<void> _continue() async {
    if (_busy || _selected == null || _workspace == null) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final workspace = _workspace!;
      await ref
          .read(workspaceProvider.notifier)
          .setWorkspace(
            companyId: workspace.companyId!,
            companyName: workspace.name,
            branchId: _selected!.id,
            branchName: _selected!.name,
            role: workspace.role,
            permissions: workspace.permissions,
          );
      if (mounted) context.go('/checking-workspace');
    } catch (error) {
      if (mounted) setState(() => _error = coreFlowError(error));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => CoreFlowPage(
    title: 'Choose branch',
    onBack: () => context.go('/account/workspaces'),
    onRefresh: _busy ? null : _refresh,
    children: [
      const CoreHero(
        eyebrow: 'WORKSPACE',
        title: 'Choose your active\nbranch',
        description: 'Switching branches clears old tenant data before the next context loads.',
      ),
      const SizedBox(height: 16),
      FutureBuilder<List<WorkspaceBranch>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Padding(
              padding: EdgeInsets.all(32),
              child: Center(child: CircularProgressIndicator()),
            );
          }
          if (snapshot.hasError) {
            return Column(
              children: [
                CoreError(coreFlowError(snapshot.error)),
                TextButton(onPressed: _refresh, child: const Text('Try again')),
              ],
            );
          }
          final branches = snapshot.data ?? const [];
          if (branches.isEmpty) {
            return Column(
              children: [
                const Text(
                  'No selectable branches are available for this membership.',
                ),
                TextButton(
                  onPressed: () => context.go('/checking-workspace'),
                  child: const Text('Continue with assigned workspace'),
                ),
              ],
            );
          }
          return CoreGroup(
            children: [
              for (final branch in branches)
                CoreChoice(
                  title: branch.name,
                  subtitle: branch.location,
                  icon: Icons.warehouse_outlined,
                  selected: _selected?.id == branch.id,
                  active: branch.id == ref.watch(workspaceProvider).branchId,
                  onTap: _busy
                      ? null
                      : () => setState(() => _selected = branch),
                ),
            ],
          );
        },
      ),
      if (_error != null) CoreError(_error!),
      const SizedBox(height: 12),
      FilledButton(
        onPressed: _selected == null || _busy ? null : _continue,
        child: Text(_busy ? 'Switching…' : 'Continue'),
      ),
    ],
  );
}
