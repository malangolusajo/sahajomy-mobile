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
import '../features/cargo_admin/bookings/presentation/cargo_bookings_page.dart';
import '../features/cargo_admin/bookings/presentation/cargo_booking_detail_page.dart';
import '../features/cargo_admin/containers/presentation/cargo_containers_page.dart';
import '../features/cargo_admin/containers/presentation/cargo_container_detail_page.dart';
import '../features/cargo_admin/receipts/presentation/cargo_receipts_page.dart';
import '../features/cargo_admin/dashboard/presentation/cargo_account_page.dart';
import '../features/cargo_admin/warehouses/presentation/cargo_warehouses_page.dart';
import '../features/cargo_admin/warehouses/presentation/cargo_warehouse_qr_page.dart';
import '../features/cargo_admin/warehouse_automation/presentation/cargo_warehouse_scanner_page.dart';
import '../features/cargo_admin/warehouse_automation/presentation/cargo_scan_result_pages.dart';
import '../features/cargo_admin/warehouse_automation/presentation/cargo_intake_pages.dart';
import '../features/cargo_admin/reservations/presentation/cargo_reservations_page.dart';
import '../features/cargo_admin/operations/presentation/cargo_operations_pages.dart';
import '../features/cargo_admin/receipts/presentation/cargo_document_detail_page.dart';
import '../features/cargo_admin/air_cargo/presentation/cargo_air_pages.dart';
import '../features/cargo_admin/staff/presentation/cargo_staff_page.dart';
import '../features/cargo_admin/notifications/presentation/cargo_notifications_page.dart';
import '../features/cargo_admin/customs/presentation/cargo_customs_pages.dart';
import '../features/booking/data/guided_booking_repository.dart';
import '../features/booking/presentation/guided_sea_booking_page.dart';
import '../features/booking/presentation/booking_hub_page.dart';
import '../features/booking/presentation/sea_cargo_services_page.dart';
import '../features/booking/presentation/sea_cargo_details_page.dart';
import '../features/booking/presentation/sea_review_booking_page.dart';
import '../features/booking/presentation/air_cargo_services_page.dart';
import '../features/booking/presentation/air_cargo_details_page.dart';
import '../features/booking/presentation/air_review_booking_page.dart';
import '../features/booking/presentation/my_bookings_page.dart';
import '../features/customer/dashboard/presentation/customer_shell.dart';
import '../features/customer/tracking/presentation/shipment_tracking_page.dart';
import '../features/customer/warehouse_access/presentation/collection_entry_page.dart';
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
import '../features/customer/china_addresses/presentation/china_address_detail_page.dart';
import '../features/customer/china_addresses/presentation/forwarding_profile_page.dart';
import '../features/customer/china_addresses/presentation/prepare_china_address_page.dart';
import '../features/customer/documents/presentation/shipping_mark_page.dart';
import '../features/customer/documents/presentation/invoice_receipt_detail_page.dart';
import '../features/customer/sourcing/presentation/search_products_agents_page.dart';
import '../features/customer/sourcing/presentation/sourcing_agent_page.dart';
import '../features/customer/sourcing/presentation/product_details_page.dart';
import '../features/customer/sourcing/presentation/sourcing_request_submitted_page.dart';
import '../features/customer/sourcing/presentation/sourcing_order_detail_page.dart';
import '../features/customer/warehouse_access/presentation/collection_code_expired_page.dart';
import '../features/customer/account/presentation/help_support_page.dart';
import '../features/customer/account/presentation/privacy_security_page.dart';
import '../features/customer/fcl_quote/presentation/fcl_quote_intro_page.dart';
import '../features/customer/fcl_quote/presentation/fcl_quote_route_page.dart';
import '../features/customer/fcl_quote/presentation/fcl_quote_cargo_page.dart';
import '../features/customer/fcl_quote/presentation/fcl_quote_review_page.dart';
import '../features/customer/fcl_quote/presentation/fcl_quote_submitted_page.dart';
import '../features/customer/fcl_quote/presentation/fcl_quote_requests_page.dart';
import '../features/customer/fcl_quote/presentation/fcl_quote_detail_page.dart';
import '../features/customer/fcl_quote/presentation/fcl_quote_cancel_page.dart';
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
        path: '/customer/booking-hub',
        builder: (context, state) => const BookingHubPage(),
      ),
      GoRoute(
        path: '/customer/booking/sea-services',
        builder: (context, state) => const SeaCargoServicesPage(),
      ),
      GoRoute(
        path: '/customer/booking/sea-details',
        builder: (context, state) => SeaCargoDetailsPage(
          containerId: state.uri.queryParameters['container_id'] ?? '',
          routeName: state.uri.queryParameters['route'] ?? '',
        ),
      ),
      GoRoute(
        path: '/customer/booking/sea-review',
        builder: (context, state) {
          final p = state.uri.queryParameters;
          return SeaReviewBookingPage(
            containerId: p['container_id'] ?? '',
            routeName: p['route'] ?? '',
            volume: p['volume'] ?? '',
            goodsType: p['goods_type'] ?? '',
            description: p['description'] ?? '',
            quantity: p['quantity'] ?? '',
            cartons: p['cartons'],
          );
        },
      ),
      GoRoute(
        path: '/customer/booking/air-services',
        builder: (context, state) => const AirCargoServicesPage(),
      ),
      GoRoute(
        path: '/customer/booking/air-details',
        builder: (context, state) {
          final p = state.uri.queryParameters;
          return AirCargoDetailsPage(
            warehouseId: p['warehouse_id'] ?? '',
            cargoAdminId: p['cargo_admin_id'] ?? '',
            companyName: p['company_name'] ?? '',
            warehouseName: p['warehouse_name'] ?? '',
          );
        },
      ),
      GoRoute(
        path: '/customer/booking/air-review',
        builder: (context, state) {
          final p = state.uri.queryParameters;
          return AirReviewBookingPage(
            warehouseId: p['warehouse_id'] ?? '',
            cargoAdminId: p['cargo_admin_id'] ?? '',
            companyName: p['company_name'] ?? '',
            warehouseName: p['warehouse_name'] ?? '',
            cargoTypeId: p['cargo_type_id'] ?? '',
            weight: p['weight'] ?? '',
            destination: p['destination'] ?? '',
            country: p['country'] ?? '',
            cartons: p['cartons'] ?? '1',
            shipmentDate: p['shipment_date'] ?? '',
            description: p['description'],
          );
        },
      ),
      GoRoute(
        path: '/customer/my-bookings',
        builder: (context, state) => const MyBookingsPage(),
      ),
      GoRoute(
        path: '/cargo-admin',
        builder: (context, state) => const CargoAdminShell(),
      ),
      GoRoute(path: '/cargo/bookings/:id', builder: (context, state) => CargoBookingDetailPage(bookingId: state.pathParameters['id'] ?? '')),
      GoRoute(path: '/cargo/bookings/:id/packing-list', builder: (context, state) => CargoBookingDetailPage(bookingId: state.pathParameters['id'] ?? '')),
      GoRoute(path: '/cargo/containers', builder: (context, state) => const CargoContainersPage()),
      GoRoute(path: '/cargo/containers/new', builder: (context, state) => const CargoCreateContainerPage()),
      GoRoute(path: '/cargo/containers/:id', builder: (context, state) => CargoContainerDetailPage(containerId: state.pathParameters['id'] ?? '')),
      GoRoute(path: '/cargo/containers/:id/packing-list', builder: (context, state) => CargoContainerDetailPage(containerId: state.pathParameters['id'] ?? '')),
      GoRoute(path: '/cargo/receipts', builder: (context, state) => const CargoReceiptsPage()),
      GoRoute(path: '/cargo/receipts/:id', builder: (context, state) => const CargoReceiptsPage()),
      GoRoute(path: '/cargo/warehouses', builder: (context, state) => const CargoWarehousesPage()),
      GoRoute(path: '/cargo/warehouses/new', builder: (context, state) => const CargoAddWarehousePage()),
      GoRoute(path: '/cargo/warehouses/:id', builder: (context, state) => CargoWarehouseDetailPage(warehouseId: state.pathParameters['id'] ?? '')),
      GoRoute(path: '/cargo/warehouses/:id/qr', builder: (context, state) => CargoWarehouseQrPage(warehouseId: state.pathParameters['id'] ?? '')),
      GoRoute(path: '/cargo/warehouses/:id/qr/fullscreen', builder: (context, state) => const CargoWarehouseQrFullscreenPage()),
      GoRoute(path: '/cargo/warehouses/:id/qr/revoked', builder: (context, state) => const CargoWarehouseQrRevokedPage()),
      GoRoute(path: '/cargo/warehouses/:id/china-address', builder: (context, state) => CargoWarehouseDetailPage(warehouseId: state.pathParameters['id'] ?? '')),
      GoRoute(path: '/cargo/scanner', builder: (context, state) => CargoWarehouseScannerPage(warehouseId: state.uri.queryParameters['warehouse_id'] ?? '')),
      GoRoute(path: '/cargo/scanner/matched', builder: (context, state) => ScanMatchedPage(result: state.extra as Map<String, dynamic>?, warehouseId: state.uri.queryParameters['warehouse_id'])),
      GoRoute(path: '/cargo/scanner/unmatched', builder: (context, state) => ScanUnmatchedPage(result: state.extra as Map<String, dynamic>?)),
      GoRoute(path: '/cargo/scanner/duplicate', builder: (context, state) => ScanDuplicatePage(result: state.extra as Map<String, dynamic>?)),
      GoRoute(path: '/cargo/scanner/low-confidence', builder: (context, state) => ScanLowConfidencePage(result: state.extra as Map<String, dynamic>?)),
      GoRoute(path: '/cargo/scanner/invalid-label', builder: (context, state) => const ScanInvalidLabelPage()),
      GoRoute(path: '/cargo/scanner/manual', builder: (context, state) => CargoManualIntakePage(warehouseId: (state.extra as Map<String, dynamic>?)?['warehouse_id'])),
      GoRoute(path: '/cargo/scanner/choose-label', builder: (context, state) => CargoChooseLabelImagePage(warehouseId: (state.extra as Map<String, dynamic>?)?['warehouse_id'])),
      GoRoute(path: '/cargo/scanner/camera-permission', builder: (context, state) => const CargoCameraPermissionPage()),
      GoRoute(path: '/cargo/scanner/offline-queue', builder: (context, state) => const CargoOfflineScanQueuePage()),
      GoRoute(path: '/cargo/scanner/history', builder: (context, state) => const CargoScanHistoryPage()),
      GoRoute(path: '/cargo/reservations', builder: (context, state) => CargoReservationsPage(containerId: state.uri.queryParameters['container_id'])),
      GoRoute(path: '/cargo/reservations/:id', builder: (context, state) => CargoReservationDetailPage(reservationId: state.pathParameters['id'] ?? '')),
      GoRoute(path: '/cargo/reservations/:id/packing-list', builder: (context, state) => CargoReservationDetailPage(reservationId: state.pathParameters['id'] ?? '')),
      GoRoute(path: '/cargo/containers/:id/consolidated-packing-list', builder: (context, state) => CargoConsolidatedPackingListPage(containerId: state.pathParameters['id'] ?? '')),
      GoRoute(path: '/cargo/containers/:id/loading-checklist', builder: (context, state) => CargoLoadingChecklistPage(containerId: state.pathParameters['id'] ?? '')),
      GoRoute(path: '/cargo/tracking/update', builder: (context, state) => CargoTrackingUpdatePage(entityId: state.uri.queryParameters['id'] ?? '')),
      GoRoute(path: '/cargo/collection/requests', builder: (context, state) => const CargoCollectionRequestsPage()),
      GoRoute(path: '/cargo/collection/verify', builder: (context, state) => const CargoVerifyCollectionPage()),
      GoRoute(path: '/cargo/collection/confirm', builder: (context, state) => const CargoConfirmHandoverPage()),
      GoRoute(path: '/cargo/collection/pin-entry', builder: (context, state) => const CargoCollectionPinEntryPage()),
      GoRoute(path: '/cargo/collection/code-used', builder: (context, state) => const CargoCollectionCodeUsedPage()),
      GoRoute(path: '/cargo/receipts/:id', builder: (context, state) => CargoDocumentDetailPage(documentId: state.pathParameters['id'] ?? '', type: state.uri.queryParameters['type'] ?? 'receipt')),
      GoRoute(path: '/cargo/air-schedules', builder: (context, state) => const CargoAirSchedulesPage()),
      GoRoute(path: '/cargo/air-schedules/new', builder: (context, state) => const CargoCreateAirSchedulePage()),
      GoRoute(path: '/cargo/air-schedules/:id', builder: (context, state) => CargoAirScheduleDetailPage(scheduleId: state.pathParameters['id'] ?? '')),
      GoRoute(path: '/cargo/air-bookings', builder: (context, state) => const CargoAirBookingsPage()),
      GoRoute(path: '/cargo/air-bookings/:id', builder: (context, state) => CargoAirBookingDetailPage(bookingId: state.pathParameters['id'] ?? '')),
      GoRoute(path: '/cargo/staff', builder: (context, state) => const CargoStaffPage()),
      GoRoute(path: '/cargo/staff/new', builder: (context, state) => const CargoCreateStaffPage()),
      GoRoute(path: '/cargo/workspace/branch', builder: (context, state) => const CargoBranchWorkspacePage()),
      GoRoute(path: '/cargo/notifications', builder: (context, state) => const CargoNotificationsPage()),
      GoRoute(path: '/cargo/customs', builder: (context, state) => const CargoCustomsDashboardPage()),
      GoRoute(path: '/cargo/customs/shipments/:id', builder: (context, state) => CargoCustomsShipmentPage(shipmentId: state.pathParameters['id'] ?? '')),
      GoRoute(path: '/cargo/customs/shipments/:id/documents', builder: (context, state) => CargoCustomsDocumentsPage(shipmentId: state.pathParameters['id'] ?? '')),
      GoRoute(path: '/cargo/customs/shipments/:id/update-status', builder: (context, state) => CargoCustomsUpdateStatusPage(shipmentId: state.pathParameters['id'] ?? '')),
      GoRoute(path: '/cargo/customs/shipments/:id/release', builder: (context, state) => CargoCustomsReleasePage(shipmentId: state.pathParameters['id'] ?? '')),
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
        builder: (_, _) => const ShipmentListPage(),
      ),
      GoRoute(
        path: '/customer/track-shipment/:ref',
        builder: (context, state) => ShipmentTrackingPage(
          entityId: state.pathParameters['ref'],
        ),
      ),
      GoRoute(
        path: '/customer/bookings',
        redirect: (context, state) => '/customer/my-bookings',
      ),
      GoRoute(
        path: '/customer/privacy',
        builder: (context, state) => const PrivacySecurityPage(),
      ),
      GoRoute(
        path: '/customer/support',
        builder: (context, state) => const HelpSupportPage(),
      ),
      GoRoute(
        path: '/customer/fcl-quote',
        builder: (context, state) => const FclQuoteIntroPage(),
      ),
      GoRoute(
        path: '/customer/fcl-quote/route',
        builder: (context, state) => const FclQuoteRoutePage(),
      ),
      GoRoute(
        path: '/customer/fcl-quote/cargo',
        builder: (context, state) => FclQuoteCargoPage(routeData: state.extra as Map<String, dynamic>?),
      ),
      GoRoute(
        path: '/customer/fcl-quote/review',
        builder: (context, state) => FclQuoteReviewPage(quoteData: state.extra as Map<String, dynamic>?),
      ),
      GoRoute(
        path: '/customer/fcl-quote/submitted',
        builder: (context, state) => const FclQuoteSubmittedPage(),
      ),
      GoRoute(
        path: '/customer/fcl-quote/requests',
        builder: (context, state) => const FclQuoteRequestsPage(),
      ),
      GoRoute(
        path: '/customer/fcl-quote/requests/:id',
        builder: (context, state) => FclQuoteDetailPage(requestId: state.pathParameters['id'] ?? ''),
      ),
      GoRoute(
        path: '/customer/fcl-quote/requests/:id/cancel',
        builder: (context, state) => FclQuoteCancelPage(requestId: state.pathParameters['id'] ?? ''),
      ),
      GoRoute(
        path: '/customer/china-addresses/:id',
        builder: (context, state) => ChinaAddressDetailPage(addressId: state.pathParameters['id'] ?? ''),
      ),
      GoRoute(
        path: '/customer/forwarding-profile',
        builder: (context, state) => const ForwardingProfilePage(),
      ),
      GoRoute(
        path: '/customer/prepare-china-address',
        builder: (context, state) => const PrepareChinaAddressPage(),
      ),
      GoRoute(
        path: '/customer/shipping-mark',
        builder: (context, state) => const ShippingMarkPage(),
      ),
      GoRoute(
        path: '/customer/agiza/search',
        builder: (context, state) => const SearchProductsAgentsPage(),
      ),
      GoRoute(
        path: '/customer/agiza/agent/:id',
        builder: (context, state) => SourcingAgentPage(agent: state.extra as Map<String, dynamic>? ?? {}),
      ),
      GoRoute(
        path: '/customer/agiza/product/:id',
        builder: (context, state) => ProductDetailsPage(productId: state.pathParameters['id'] ?? ''),
      ),
      GoRoute(
        path: '/customer/sourcing-request-submitted',
        builder: (context, state) => const SourcingRequestSubmittedPage(),
      ),
      GoRoute(
        path: '/customer/orders/:id',
        builder: (context, state) => SourcingOrderDetailPage(orderId: state.pathParameters['id'] ?? ''),
      ),
      GoRoute(
        path: '/customer/invoice',
        builder: (context, state) => InvoiceDetailPage(
          invoice: state.extra as Map<String, dynamic>? ?? {},
          reservationId: state.uri.queryParameters['reservation_id'],
        ),
      ),
      GoRoute(
        path: '/customer/receipt',
        builder: (context, state) => ReceiptDetailPage(
          receipt: state.extra as Map<String, dynamic>? ?? {},
          reservationId: state.uri.queryParameters['reservation_id'],
        ),
      ),
      GoRoute(
        path: '/customer/collection/expired',
        builder: (context, state) => CollectionCodeExpiredPage(
          reference: state.uri.queryParameters['reference'],
        ),
      ),
      GoRoute(
        path: '/customer/collection',
        builder: (context, state) => const CollectionEntryPage(),
      ),
      for (final entry in appRouteAliases.entries)
        GoRoute(
          path: entry.key,
          builder: (context, state) {
            if (entry.value == 'customer-sea-bookings.html' ||
                entry.value == 'customer-reservations.html') {
              return const BookingListPage();
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
