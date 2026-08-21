import 'package:flutter/material.dart';

import '../features/auth/presentation/sign_in_page.dart';
import '../features/cargo_admin/presentation/cargo_admin_shell.dart';
import '../features/customer/dashboard/presentation/customer_shell.dart';
import '../features/customer/china_addresses/presentation/china_address_list_page.dart';
import '../features/customer/containers/presentation/container_list_page.dart';
import '../features/customer/reservations/presentation/reservation_list_page.dart';
import '../features/customer/profile/presentation/customer_profile_page.dart';
import '../features/customer/air_cargo/presentation/air_cargo_booking_list_page.dart';
import '../features/customer/notifications/presentation/customer_notifications_page.dart';
import '../features/customer/tracking/presentation/shipment_tracking_page.dart';
import '../features/reference/presentation/native_reference_screen.dart';
import '../features/reference/presentation/native_screen_specs.dart';
import '../features/sourcing_agent/presentation/sourcing_agent_shell.dart';
import '../features/super_admin/presentation/super_admin_shell.dart';
import 'theme.dart';
import 'app_gate.dart';

void runSahajomyApp() => runApp(const SahajomyApp());

class SahajomyApp extends StatelessWidget {
  const SahajomyApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'Sahajomy',
    debugShowCheckedModeBanner: false,
    theme: sahajomyTheme,
    home: const AppGate(),
    routes: {
      '/sign-in': (_) => const SignInPage(),
      '/customer': (_) => const CustomerShell(),
      '/customer/track-shipment': (_) => const ShipmentTrackingPage(),
      '/customer/china-addresses': (_) => const ChinaAddressListPage(),
      '/customer/containers': (_) => const ContainerListPage(),
      '/customer/reservations': (_) => const ReservationListPage(),
      '/customer/profile': (_) => const CustomerProfilePage(),
      '/customer/express-air-cargo': (_) => const AirCargoBookingListPage(),
      '/customer/notifications': (_) => const CustomerNotificationsPage(),
      '/screens': (_) => const NativeScreenCatalog(),
      '/cargo-admin': (_) => const CargoAdminShell(),
      '/sourcing-agent': (_) => const SourcingAgentShell(),
      '/super-admin': (_) => const SuperAdminShell(),
    },
    onGenerateRoute: (settings) {
      final name = settings.name;
      if (name == null) return null;
      for (final spec in nativeScreenSpecs) {
        if (spec.routeName == name) {
          return MaterialPageRoute(
            settings: settings,
            builder: (_) => NativeReferenceScreen(spec: spec),
          );
        }
      }
      return null;
    },
  );
}
