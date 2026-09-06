import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'auth/session_store.dart';
import 'network/api_client.dart';
import 'storage/token_storage.dart';
import 'workspaces/workspace_provider.dart';

final tokenStorageProvider = Provider<TokenStorage>((ref) => TokenStorage());

/// In-memory only so sensitive app-link tokens never enter logs or storage.
final pendingDestinationProvider = StateProvider<String?>((ref) => null);

final sessionStoreProvider = Provider<SessionStore>((ref) {
  final tokenStorage = ref.watch(tokenStorageProvider);
  return SessionStore(tokenStorage);
});

final workspaceProvider =
    StateNotifierProvider<WorkspaceProvider, WorkspaceState>((ref) {
      final tokenStorage = ref.watch(tokenStorageProvider);
      return WorkspaceProvider(tokenStorage);
    });

final apiClientProvider = Provider<ApiClient>((ref) {
  final tokenStorage = ref.watch(tokenStorageProvider);
  final workspaceNotifier = ref.watch(workspaceProvider.notifier);
  return ApiClient(
    tokenStorage: tokenStorage,
    workspaceProvider: workspaceNotifier,
  );
});
