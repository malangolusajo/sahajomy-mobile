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
    ready = _loadFromStorage();
  }

  final TokenStorage _tokenStorage;
  late final Future<void> ready;
  int _revision = 0;

  String? get currentCompanyId => state.companyId;
  String? get currentBranchId => state.branchId;
  int get revision => _revision;

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
    // Invalidate old-tenant responses before waiting on device storage.
    _revision++;
    await ready;
    state = const WorkspaceState();
    await _tokenStorage.clearWorkspace();
  }

  bool hasPermission(String permission) =>
      state.permissions?.contains(permission) ?? false;

  /// Client-side defence in depth. The API remains the authority, but a
  /// company-scoped route is not rendered when its returned capability list
  /// does not permit that resource.
  bool canOpenRoute(String location) {
    if (!state.hasCompany ||
        location == '/account/workspaces' ||
        const {
          '/customer',
          '/cargo-admin',
          '/sourcing-agent',
          '/super-admin',
        }.contains(location)) {
      return true;
    }
    final permissions = state.permissions;
    if (permissions == null) return false;
    final normalized = permissions
        .map((value) => value.trim().toLowerCase())
        .where((value) => value.isNotEmpty)
        .toSet();
    if (normalized.contains('*') || normalized.contains('admin:*')) return true;
    final segments = Uri.parse(location).pathSegments;
    if (segments.length < 2) return true;
    final segment = segments[1].replaceAll('-', '_');
    if (const {'profile', 'notifications', 'account'}.contains(segment)) {
      return true;
    }
    final resource = switch (segment) {
      'bookings' || 'sea_bookings' || 'reservations' => 'booking',
      'shipments' || 'shipment_orders' => 'shipment',
      'payments' => 'payment',
      'parcels' || 'warehouse_access' => 'parcel',
      _ => segment,
    };
    final route = Uri.parse(location).path.toLowerCase();
    return normalized.contains('route:$route') ||
        normalized.contains('$resource:*') ||
        normalized.contains('$resource.read') ||
        normalized.contains('$resource.view') ||
        normalized.contains('$resource.manage');
  }
}
