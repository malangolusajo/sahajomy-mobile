import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'auth/session_store.dart';
import 'auth/mfa_challenge.dart';
import 'network/api_client.dart';
import 'storage/token_storage.dart';
import 'workspaces/workspace_provider.dart';

final tokenStorageProvider = Provider<TokenStorage>((ref) => TokenStorage());

/// In-memory only so sensitive app-link tokens never enter logs or storage.
final pendingDestinationProvider = StateProvider<String?>((ref) => null);

/// PII and MFA material stay in memory and are cleared after authentication.
final pendingPhoneNumberProvider = StateProvider<String?>((ref) => null);
final pendingEmailProvider = StateProvider<String?>((ref) => null);
final pendingMfaChallengeProvider = StateProvider<MfaChallenge?>((ref) => null);

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
  final client = ApiClient(
    tokenStorage: tokenStorage,
    workspaceProvider: workspaceNotifier,
  );
  ref.onDispose(client.close);
  return client;
});

final onboardingCompletedProvider = FutureProvider<bool>((ref) {
  return ref.watch(tokenStorageProvider).getOnboardingCompleted();
});
