import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/providers.dart';
import '../../../core/ui/sahajomy_ui.dart';
import '../../repository_providers.dart';

class WorkspaceSelectionPage extends ConsumerStatefulWidget {
  const WorkspaceSelectionPage({super.key});

  @override
  ConsumerState<WorkspaceSelectionPage> createState() =>
      _WorkspaceSelectionPageState();
}

class _WorkspaceSelectionPageState
    extends ConsumerState<WorkspaceSelectionPage> {
  late Future<List<Map<String, dynamic>>> _workspaces = Future.microtask(_load);
  String? _switchingId;

  Future<List<Map<String, dynamic>>> _load() async {
    final response = await ref
        .read(workflowApiRepositoryProvider)
        .load('workspaces');
    if (response is List) {
      return response.whereType<Map<String, dynamic>>().toList(growable: false);
    }
    if (response is Map<String, dynamic>) {
      final records =
          response['workspaces'] ?? response['items'] ?? response['data'];
      if (records is List) {
        return records.whereType<Map<String, dynamic>>().toList(
          growable: false,
        );
      }
    }
    return const [];
  }

  void _retry() => setState(() => _workspaces = Future.microtask(_load));

  Future<void> _select(Map<String, dynamic> workspace) async {
    final companyId = workspace['company_id']?.toString();
    final selectionId = companyId ?? 'personal';
    setState(() => _switchingId = selectionId);
    final notifier = ref.read(workspaceProvider.notifier);
    try {
      if (companyId == null || companyId.isEmpty) {
        await notifier.clearWorkspace();
      } else {
        await notifier.setWorkspace(
          companyId: companyId,
          companyName:
              workspace['company_name']?.toString() ??
              workspace['name']?.toString() ??
              'Company workspace',
          branchId: workspace['branch_id']?.toString(),
          branchName: workspace['branch_name']?.toString(),
          role: workspace['company_role']?.toString(),
          permissions: (workspace['permissions'] as List?)
              ?.map((permission) => permission.toString())
              .toList(growable: false),
        );
      }
      ref.invalidate(apiClientProvider);
      if (mounted) context.pop();
    } finally {
      if (mounted) setState(() => _switchingId = null);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(
      role: 'Shared',
      title: 'Switch workspace',
    ),
    body: FutureBuilder<List<Map<String, dynamic>>>(
      future: _workspaces,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return SahajomyMessageState(
            icon: Icons.cloud_off_outlined,
            message: 'Workspaces are unavailable. Check your connection and try again.',
            actionLabel: 'Try again',
            onAction: _retry,
          );
        }
        final workspaces = snapshot.data ?? const [];
        if (workspaces.isEmpty) {
          return const SahajomyMessageState(
            icon: Icons.business_outlined,
            message: 'No company workspaces are available. Your personal workspace remains active.',
          );
        }
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
          children: [
            Text(
              'Choose your workspace',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 6),
            const Text(
              'Your account role stays the same. Company role, branch, and permissions follow the selected workspace.',
            ),
            const SizedBox(height: 20),
            for (final workspace in workspaces)
              Card(
                margin: const EdgeInsets.only(bottom: 10),
                child: ListTile(
                  minTileHeight: 72,
                  leading: const Icon(Icons.business_outlined),
                  title: Text(
                    workspace['company_name']?.toString() ??
                        workspace['name']?.toString() ??
                        'Personal workspace',
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                  subtitle: Text(
                    [workspace['company_role'], workspace['branch_name']]
                        .whereType<String>()
                        .where((value) => value.isNotEmpty)
                        .join(' · '),
                  ),
                  trailing:
                      _switchingId ==
                          (workspace['company_id']?.toString() ?? 'personal')
                      ? const SizedBox.square(
                          dimension: 22,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.chevron_right_rounded),
                  onTap: _switchingId == null ? () => _select(workspace) : null,
                ),
              ),
          ],
        );
      },
    ),
  );
}
