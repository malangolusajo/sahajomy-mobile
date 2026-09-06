import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../storage/token_storage.dart';

class WorkspaceState {
  const WorkspaceState({
    this.companyId,
    this.companyName,
    this.branchId,
    this.branchName,
    this.role,
    this.permissions,
  });

  final String? companyId;
  final String? companyName;
  final String? branchId;
  final String? branchName;
  final String? role;
  final List<String>? permissions;

  WorkspaceState copyWith({
    String? companyId,
    String? companyName,
    String? branchId,
    String? branchName,
    String? role,
    List<String>? permissions,
  }) => WorkspaceState(
    companyId: companyId ?? this.companyId,
    companyName: companyName ?? this.companyName,
    branchId: branchId ?? this.branchId,
    branchName: branchName ?? this.branchName,
    role: role ?? this.role,
    permissions: permissions ?? this.permissions,
  );

  bool get hasCompany => companyId != null && companyId!.isNotEmpty;
  bool get hasBranch => branchId != null && branchId!.isNotEmpty;
}

class WorkspaceProvider extends StateNotifier<WorkspaceState> {
  WorkspaceProvider(this._tokenStorage) : super(const WorkspaceState()) {
    _loadFromStorage();
  }

  final TokenStorage _tokenStorage;

  String? get currentCompanyId => state.companyId;
  String? get currentBranchId => state.branchId;

  Future<void> _loadFromStorage() async {
    final companyId = await _tokenStorage.getCompanyId();
    final branchId = await _tokenStorage.getBranchId();
    if (companyId != null || branchId != null) {
      state = state.copyWith(companyId: companyId, branchId: branchId);
    }
  }

  Future<void> setWorkspace({
    required String companyId,
    required String companyName,
    String? branchId,
    String? branchName,
    String? role,
    List<String>? permissions,
  }) async {
    // Remove the old tenant context before persisting the new one so no
    // in-flight navigation can accidentally reuse stale company headers.
    await clearWorkspace();
    // Persist the tenant selection without touching authentication tokens.
    await _tokenStorage.saveWorkspace(companyId: companyId, branchId: branchId);
    state = state.copyWith(
      companyId: companyId,
      companyName: companyName,
      branchId: branchId,
      branchName: branchName,
      role: role,
      permissions: permissions,
    );
  }

  Future<void> clearWorkspace() async {
    await _tokenStorage.clearWorkspace();
    state = const WorkspaceState();
  }

  bool hasPermission(String permission) =>
      state.permissions?.contains(permission) ?? false;
}
