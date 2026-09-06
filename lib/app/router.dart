import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/auth/session.dart';
import '../core/providers.dart';
import '../features/auth/data/auth_repository.dart';
import '../features/auth/presentation/otp_page.dart';
import '../features/auth/presentation/sign_in_page.dart';
import '../features/auth/presentation/welcome_page.dart';
import '../features/cargo_admin/presentation/cargo_admin_shell.dart';
import '../features/booking/data/guided_booking_repository.dart';
import '../features/booking/presentation/guided_sea_booking_page.dart';
import '../features/customer/dashboard/presentation/customer_shell.dart';
import '../features/customer/warehouse_access/presentation/customer_warehouse_parcels_page.dart';
import '../features/reference/presentation/dedicated_preview_pages.dart';
import '../features/reference/presentation/native_reference_screen.dart';
import '../features/reference/presentation/native_screen_specs.dart';
import '../features/sourcing_agent/presentation/sourcing_agent_shell.dart';
import '../features/super_admin/presentation/super_admin_shell.dart';
import 'app_route_aliases.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final sessionStore = ref.watch(sessionStoreProvider);
  final apiClient = ref.watch(apiClientProvider);
  final workspaceNotifier = ref.watch(workspaceProvider.notifier);

  return GoRouter(
    initialLocation: '/',
    redirect: (context, state) async {
      final customDestination = _customSchemeDestination(state.uri);
      if (customDestination != null) return customDestination;
      final session = await sessionStore.read();
      final location = state.matchedLocation;
      final isAuthRoute =
          location == '/sign-in' || location == '/login' || location == '/otp';
      final isProtectedRoute = _isProtectedLocation(location);

      if (session == null && isProtectedRoute) {
        ref.read(pendingDestinationProvider.notifier).state = state.uri
            .toString();
        return '/sign-in';
      }
      if (session == null) return null;

      if (isProtectedRoute) {
        if (!_roleCanOpen(session.role, location)) {
          return _routeForRole(session.role);
        }

        // Protected destinations always verify the authoritative session.
        try {
          await apiClient.get(
            'auth/me',
            queryParameters: {
              if (workspaceNotifier.currentCompanyId != null)
                'company_id': workspaceNotifier.currentCompanyId,
            },
          );
        } catch (_) {
          try {
            final refreshed = await AuthRepository(apiClient)
                .refreshSession(session);
            await sessionStore.save(refreshed);
          } catch (_) {
            await sessionStore.clear();
            ref.read(pendingDestinationProvider.notifier).state = state.uri
                .toString();
            return '/sign-in';
          }
        }
      }

      if (isAuthRoute) return _routeForRole(session.role);
      return null;
    },
    routes: [
      GoRoute(
        path: '/welcome',
        builder: (context, state) => const WelcomePage(),
      ),
      GoRoute(
        path: '/sign-in',
        builder: (context, state) => const SignInPage(),
      ),
      GoRoute(
        path: '/otp',
        builder: (context, state) {
          final phone = state.uri.queryParameters['phone'] ?? '';
          return OtpPage(phoneNumber: phone);
        },
      ),
      GoRoute(
        path: '/customer',
        builder: (context, state) => const CustomerShell(),
      ),
      GoRoute(
        path: '/cargo-admin',
        builder: (context, state) => const CargoAdminShell(),
      ),
      GoRoute(
        path: '/sourcing-agent',
        builder: (context, state) => const SourcingAgentShell(),
      ),
      GoRoute(
        path: '/super-admin',
        builder: (context, state) => const SuperAdminShell(),
      ),
      GoRoute(
        path: '/screens',
        builder: (context, state) => const NativeScreenCatalog(),
      ),
      GoRoute(
        path: '/customer/sea-bookings/new',
        builder: (context, state) => GuidedSeaBookingPage(
          account: BookingAccount.customer,
          initialContainerId: state.uri.queryParameters['container_id'],
        ),
      ),
      GoRoute(
        path: '/agent/sea-bookings/new',
        builder: (context, state) => GuidedSeaBookingPage(
          account: BookingAccount.sourcingAgent,
          initialContainerId: state.uri.queryParameters['container_id'],
        ),
      ),
      for (final entry in appRouteAliases.entries)
        GoRoute(
          path: entry.key,
          builder: (context, state) {
            if (entry.value == 'customer-warehouse-parcels.html') {
              return CustomerWarehouseParcelsPage(
                opaqueToken: state.pathParameters['token'] ?? '',
              );
            }
            return dedicatedPreviewPageFor(nativeScreenSpecFor(entry.value));
          },
        ),
      for (final spec in nativeScreenSpecs)
        GoRoute(
          path: spec.routeName,
          builder: (context, state) => dedicatedPreviewPageFor(spec),
        ),
    ],
  );
});

bool _isProtectedLocation(String location) =>
    location == '/customer' ||
    location.startsWith('/customer/') ||
    location == '/sourcing-agent' ||
    location.startsWith('/agent/') ||
    location == '/cargo-admin' ||
    location.startsWith('/cargo/') ||
    location == '/super-admin' ||
    location.startsWith('/admin/') ||
    location == '/account/workspaces';

String? _customSchemeDestination(Uri uri) {
  if (uri.scheme != 'sahajomy' && uri.scheme != 'sajajomy') return null;
  final segments = uri.pathSegments;
  if (uri.host == 'customer' &&
      segments.length >= 2 &&
      segments[0] == 'warehouse-access') {
    return '/customer/warehouse-access/${Uri.encodeComponent(segments[1])}';
  }
  if (uri.host == 'shared' && segments.length >= 3 && segments[0] == 'label') {
    return '/label/${segments[1]}/${Uri.encodeComponent(segments[2])}';
  }
  if (uri.host == 'shared' &&
      segments.length >= 2 &&
      segments[0] == 'product') {
    return '/product/${Uri.encodeComponent(segments[1])}';
  }
  if (uri.host == 'shared' && segments.length >= 2 && segments[0] == 'batch') {
    return '/shared/${Uri.encodeComponent(segments[1])}';
  }
  if (uri.host == 'verify-receipt' && segments.isNotEmpty) {
    return Uri(
      path: '/verify-receipt',
      queryParameters: {'code': segments.first},
    ).toString();
  }
  return '/';
}

bool _roleCanOpen(UserRole role, String location) {
  if (location == '/account/workspaces') return true;
  return switch (role) {
    UserRole.customer =>
      location == '/customer' || location.startsWith('/customer/'),
    UserRole.sourcingAgent =>
      location == '/sourcing-agent' || location.startsWith('/agent/'),
    UserRole.cargoAdmin =>
      location == '/cargo-admin' || location.startsWith('/cargo/'),
    UserRole.superAdmin =>
      location == '/super-admin' || location.startsWith('/admin/'),
  };
}

String _routeForRole(UserRole role) => switch (role) {
  UserRole.customer => '/customer',
  UserRole.cargoAdmin => '/cargo-admin',
  UserRole.sourcingAgent => '/sourcing-agent',
  UserRole.superAdmin => '/super-admin',
};
