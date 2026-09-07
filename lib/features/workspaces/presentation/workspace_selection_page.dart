import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/providers.dart';
import '../../../core/ui/core_flow_ui.dart';
import '../data/workspace_repository.dart';

class WorkspaceSelectionPage extends ConsumerStatefulWidget {
  const WorkspaceSelectionPage({super.key});
  @override
  ConsumerState<WorkspaceSelectionPage> createState() =>
      _WorkspaceSelectionPageState();
}

class _WorkspaceSelectionPageState
    extends ConsumerState<WorkspaceSelectionPage> {
  late Future<List<Workspace>> _future;
  Workspace? _selected;
  bool _busy = false;
  String? _error;
  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<Workspace>> _load() =>
      ref.read(workspaceRepositoryProvider).list();
  Future<void> _refresh() async {
    setState(() {
      _selected = null;
      _future = _load();
    });
    try {
      await _future;
    } catch (_) {
      /* Render the FutureBuilder error. */
    }
  }

  Future<void> _continue() async {
    if (_busy || _selected == null) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final selected = _selected!;
      final notifier = ref.read(workspaceProvider.notifier);
      if (selected.isPersonal) {
        await notifier.clearWorkspace();
      } else {
        await notifier.setWorkspace(
          companyId: selected.companyId!,
          companyName: selected.name,
          branchId: selected.branchId,
          branchName: selected.branchName,
          role: selected.role,
          permissions: selected.permissions,
        );
      }
      if (!mounted) return;
      context.go(
        !selected.isPersonal &&
                selected.permissions.contains('company.branch.manage')
            ? '/account/branches'
            : '/checking-workspace',
      );
    } catch (error) {
      if (mounted) setState(() => _error = coreFlowError(error));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => CoreFlowPage(
    title: 'Switch workspace',
    onBack: () => context.go('/checking-workspace'),
    onRefresh: _busy ? null : _refresh,
    children: [
      const CoreHero(
        eyebrow: 'WORKSPACE',
        title: 'Choose how you want\nto use Sahajomy',
        description: 'Switching workspaces clears old tenant data before the next context loads.',
      ),
      const SizedBox(height: 16),
      FutureBuilder<List<Workspace>>(
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
          final items = snapshot.data ?? const [];
          if (items.isEmpty) {
            return const Text(
              'No workspaces are available for this account. Pull down to check again.',
            );
          }
          return CoreGroup(
            children: [
              for (final item in items)
                CoreChoice(
                  title: item.name,
                  subtitle: item.isPersonal
                      ? 'Your account workspace'
                      : [
                          item.role,
                          item.branchName,
                        ].whereType<String>().join(' · '),
                  icon: item.isPersonal
                      ? Icons.person_outline
                      : Icons.business_outlined,
                  selected: _selected?.id == item.id,
                  active:
                      item.companyId == ref.watch(workspaceProvider).companyId,
                  onTap: _busy ? null : () => setState(() => _selected = item),
                ),
            ],
          );
        },
      ),
      if (_error != null) CoreError(_error!),
      const SizedBox(height: 12),
      FilledButton(
        onPressed: _busy || _selected == null ? null : _continue,
        child: Text(_busy ? 'Switching…' : 'Continue'),
      ),
    ],
  );
}
