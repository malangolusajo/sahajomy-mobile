import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/auth/session.dart';
import '../core/providers.dart';
import '../core/network/api_exception.dart';
import '../core/security/app_link_guard.dart';
import '../features/auth/data/auth_repository.dart';
import '../features/auth/presentation/mfa_page.dart';
import '../features/auth/presentation/otp_page.dart';
import '../features/auth/presentation/auth_status_page.dart';
import '../features/auth/presentation/stay_updated_page.dart';
import '../features/workspaces/presentation/branch_selection_page.dart';
import '../features/workspaces/presentation/checking_workspace_page.dart';
import '../features/auth/presentation/registration_page.dart';
import '../features/auth/presentation/sign_in_page.dart';
import '../features/auth/presentation/welcome_page.dart';
import '../features/cargo_admin/presentation/cargo_admin_shell.dart';
import '../features/booking/data/guided_booking_repository.dart';
import '../features/booking/presentation/guided_sea_booking_page.dart';
import '../features/customer/dashboard/presentation/customer_shell.dart';
import '../features/customer/warehouse_access/presentation/customer_warehouse_parcels_page.dart';
import '../features/onboarding/presentation/onboarding_page.dart';
import '../features/onboarding/presentation/splash_page.dart';
import '../features/reference/presentation/dedicated_preview_pages.dart';
import '../features/reference/presentation/native_reference_screen.dart';
import '../features/reference/presentation/native_screen_specs.dart';
import '../features/reference/presentation/record_detail_page.dart';
import '../features/customer/reservations/presentation/booking_detail_page.dart';
import '../features/customer/reservations/presentation/booking_list_page.dart';
import '../features/customer/shipments/presentation/shipment_list_page.dart';
import '../features/sourcing_agent/presentation/sourcing_agent_shell.dart';
import '../features/super_admin/presentation/super_admin_shell.dart';
import 'app_route_aliases.dart';
import 'theme.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final sessionStore = ref.watch(sessionStoreProvider);
  final apiClient = ref.watch(apiClientProvider);
  final workspaceNotifier = ref.watch(workspaceProvider.notifier);

  return GoRouter(
    initialLocation: '/splash',
    redirect: (context, state) async {
      final location = state.matchedLocation;
      // The splash page owns the initial session/onboarding decision so the
      // branded transition is shown consistently instead of flashing a route.
      if (location == '/splash') return null;
      // These pages own their async verification and recovery UI. Never hide
      // their offline/permission states behind an eager route redirect.
      if (const {
        '/checking-workspace',
        '/account/workspaces',
        '/account/branches',
        '/stay-updated',
      }.contains(location)) {
        return await sessionStore.read() == null ? '/sign-in' : null;
      }

      final session = await sessionStore.read();
      final isAuthRoute =
          location == '/sign-in' ||
          location == '/login' ||
          location == '/register' ||
          location == '/otp' ||
          location == '/mfa' ||
          location == '/onboarding';
      final isProtectedRoute = _isProtectedLocation(location);

      if (session == null && isProtectedRoute) {
        ref.read(pendingDestinationProvider.notifier).state =
            sanitizePendingDestination(state.uri.toString());
        return '/sign-in';
      }
      if (session == null) return null;

      if (isProtectedRoute || isAuthRoute) {
        // Never trust the persisted role. Every protected transition checks
        // the server-authoritative identity and MFA state first.
        try {
          await workspaceNotifier.ready;
          final verified = await AuthRepository(apiClient)
              .verifyStoredSession(session);
          await sessionStore.save(verified);
          if (isProtectedRoute && !_roleCanOpen(verified.role, location)) {
            return _routeForRole(verified.role);
          }
          if (isProtectedRoute && !workspaceNotifier.canOpenRoute(location)) {
            return _routeForRole(verified.role);
          }
          if (isAuthRoute) return _routeForRole(verified.role);
        } on ApiException catch (error) {
          if (!error.isUnauthorized && !error.isForbidden) {
            ref.read(pendingDestinationProvider.notifier).state =
                sanitizePendingDestination(state.uri.toString());
            return '/splash';
          }
          await workspaceNotifier.clearWorkspace();
          await sessionStore.clear();
          ref.read(pendingDestinationProvider.notifier).state =
              sanitizePendingDestination(state.uri.toString());
          return '/sign-in';
        } on FormatException {
          await workspaceNotifier.clearWorkspace();
          await sessionStore.clear();
          return '/sign-in';
        } catch (_) {
          ref.read(pendingDestinationProvider.notifier).state =
              sanitizePendingDestination(state.uri.toString());
          return '/splash';
        }
      }

      return null;
    },
    routes: [
      GoRoute(
        path: '/splash',
        builder: (context, state) =>
            Theme(data: sahajomyTheme, child: const SplashPage()),
      ),
      GoRoute(
        path: '/onboarding',
        builder: (context, state) =>
            Theme(data: sahajomyTheme, child: const OnboardingPage()),
      ),
      GoRoute(
        path: '/welcome',
        builder: (context, state) => const WelcomePage(),
      ),
      GoRoute(
        path: '/sign-in',
        builder: (context, state) => const SignInPage(),
      ),
      GoRoute(
        path: '/register',
        builder: (context, state) => const RegistrationPage(),
      ),
      GoRoute(path: '/otp', builder: (context, state) => const OtpPage()),
      GoRoute(
        path: '/code-expired',
        builder: (context, state) => const AuthStatusPage(),
      ),
      GoRoute(
        path: '/account-suspended',
        builder: (context, state) => const AuthStatusPage(suspended: true),
      ),
      GoRoute(
        path: '/stay-updated',
        builder: (context, state) => const StayUpdatedPage(),
      ),
      GoRoute(
        path: '/account/branches',
        builder: (context, state) => const BranchSelectionPage(),
      ),
      GoRoute(
        path: '/checking-workspace',
        builder: (context, state) => const CheckingWorkspacePage(),
      ),
      GoRoute(path: '/mfa', builder: (context, state) => const MfaPage()),
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
      if (kDebugMode)
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
      GoRoute(
        path: '/customer/shipments',
        builder: (_, _) => Scaffold(
          appBar: AppBar(title: const Text('My shipments')),
          body: const ShipmentListPage(),
        ),
      ),
      for (final entry in appRouteAliases.entries)
        GoRoute(
          path: entry.key,
          builder: (context, state) {
            if (entry.value == 'customer-sea-bookings.html' ||
                entry.value == 'customer-reservations.html') {
              return Scaffold(
                appBar: AppBar(title: const Text('Sea freight bookings')),
                body: const BookingListPage(),
              );
            }
            final bookingId = state.pathParameters['seaBookingId'];
            if (entry.value == 'customer-sea-booking-detail.html' &&
                bookingId != null) {
              return BookingDetailPage(bookingId: bookingId);
            }
            final detail = switch (entry.key) {
              '/customer/shipment-orders/:shipmentOrderId' => (
                'Shipment details',
                'customer/shipment-orders/${Uri.encodeComponent(state.pathParameters['shipmentOrderId']!)}',
              ),
              '/admin/companies/:companyId' => (
                'Cargo company',
                'super_admin/companies/${Uri.encodeComponent(state.pathParameters['companyId']!)}',
              ),
              '/agizisha/product/:id' => (
                'Product details',
                'public/agizisha/products/${Uri.encodeComponent(state.pathParameters['id']!)}',
              ),
              '/product/:productId' => (
                'Product details',
                'public/agizisha/products/${Uri.encodeComponent(state.pathParameters['productId']!)}',
              ),
              '/agizisha/agents/:handle' => (
                'Sourcing agent',
                'public/agizisha/agents/${Uri.encodeComponent(state.pathParameters['handle']!)}',
              ),
              '/shared/:token' => (
                'Shared sourcing batch',
                'public/batch/${Uri.encodeComponent(state.pathParameters['token']!)}',
              ),
              '/agent/packing-lists/:packingListId' => (
                'Packing list',
                'sourcing_agent/packing-lists/${Uri.encodeComponent(state.pathParameters['packingListId']!)}',
              ),
              _ => null,
            };
            if (detail != null) {
              return RecordDetailPage(title: detail.$1, endpoint: detail.$2);
            }
            if (entry.value == 'customer-warehouse-parcels.html') {
              return CustomerWarehouseParcelsPage(
                opaqueToken: state.pathParameters['token'] ?? '',
              );
            }
            return dedicatedPreviewPageFor(nativeScreenSpecFor(entry.value));
          },
        ),
      if (kDebugMode)
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
