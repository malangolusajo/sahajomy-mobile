import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../../../core/providers.dart';

final workspaceRepositoryProvider = Provider(
  (ref) => WorkspaceRepository(ref.watch(apiClientProvider)),
);

class Workspace {
  const Workspace({
    required this.id,
    required this.name,
    this.companyId,
    this.branchId,
    this.branchName,
    this.role,
    this.roleId,
    this.permissions = const [],
  });
  final String id, name;
  final String? companyId, branchId, branchName, role, roleId;
  final List<String> permissions;
  bool get isPersonal => companyId == null;
  factory Workspace.fromJson(Map<String, dynamic> json) => Workspace(
    id: json['id'] as String,
    name: (json['company_name'] ?? json['name']) as String,
    companyId: json['company_id'] as String?,
    branchId: json['branch_id'] as String?,
    branchName: json['branch_name'] as String?,
    role: json['role'] as String?,
    roleId: json['role_id'] as String?,
    permissions: (json['permissions'] as List? ?? const []).cast<String>(),
  );
}

class WorkspaceBranch {
  const WorkspaceBranch({
    required this.id,
    required this.name,
    required this.location,
  });
  final String id, name, location;
  factory WorkspaceBranch.fromJson(Map<String, dynamic> json) =>
      WorkspaceBranch(
        id: json['id'] as String,
        name: json['name'] as String,
        location: [
          json['city'],
          json['country'],
        ].whereType<String>().join(' · '),
      );
}

class WorkspaceRepository {
  WorkspaceRepository(this._api);
  final ApiClient _api;
  Future<List<Workspace>> list() async {
    final data = await _api.get<Map<String, dynamic>>(
      'workspaces',
      options: Options(extra: {'skipTenant': true}),
    );
    return [
      if (data['personal'] is Map<String, dynamic>)
        Workspace.fromJson(data['personal'] as Map<String, dynamic>),
      for (final json in (data['companies'] as List? ?? const []))
        Workspace.fromJson(Map<String, dynamic>.from(json as Map)),
    ];
  }

  /// Resolves membership and branch through the backend's workspace dependency.
  Future<void> verifyContext() async {
    await _api.get<List<dynamic>>('workspaces/roles');
  }

  Future<List<WorkspaceBranch>> branches(Workspace workspace) async {
    if (!workspace.permissions.contains('company.branch.manage')) {
      return const [];
    }
    final roles = await _api.get<List<dynamic>>('workspaces/roles');
    final role = roles
        .whereType<Map>()
        .where((role) => role['id'] == workspace.roleId)
        .firstOrNull;
    final list = await _api.get<List<dynamic>>('workspaces/branches');
    return list
        .whereType<Map>()
        .where(
          (branch) =>
              role?['scope'] == 'company' || branch['id'] == workspace.branchId,
        )
        .map(
          (json) => WorkspaceBranch.fromJson(Map<String, dynamic>.from(json)),
        )
        .toList();
  }
}
