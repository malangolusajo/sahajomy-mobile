import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sahajomy_mobile/app/operational_theme.dart';
import 'package:sahajomy_mobile/core/network/api_client.dart';
import 'package:sahajomy_mobile/core/providers.dart';
import 'package:sahajomy_mobile/core/storage/token_storage.dart';
import 'package:sahajomy_mobile/core/workspaces/workspace_provider.dart';
import 'package:sahajomy_mobile/features/booking/data/guided_booking_repository.dart';
import 'package:sahajomy_mobile/features/booking/presentation/guided_sea_booking_page.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final view =
      TestWidgetsFlutterBinding.instance.platformDispatcher.views.first;
  view.physicalSize = const Size(800, 1200);
  view.devicePixelRatio = 1.0;
  for (final account in BookingAccount.values) {
    testWidgets(
      '${account.name}: address preparation, review, and correct booking schema',
      (tester) async {
        FlutterSecureStorage.setMockInitialValues({});
        final api = _BookingApi(TokenStorage());
        await tester.pumpWidget(
          ProviderScope(
            overrides: [apiClientProvider.overrideWithValue(api)],
            child: MaterialApp(
              theme: operationalTheme,
              home: GuidedSeaBookingPage(
                account: account,
                initialContainerId: 'container-42',
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();
        expect(api.mutations, isEmpty);
        await tester.enterText(
          find.widgetWithText(TextFormField, 'Cargo volume (CBM)'),
          '2.5',
        );
        await tester.enterText(
          find.widgetWithText(TextFormField, 'Destination city'),
          'Arusha',
        );
        await tester.enterText(
          find.widgetWithText(TextFormField, 'Destination country'),
          'Tanzania',
        );
        final review = find.text('Review cargo booking');
        await tester.ensureVisible(review);
        await tester.tap(review, warnIfMissed: false);
        await tester.pumpAndSettle();
        expect(api.mutations.single.$1, 'forwarding/prepare-address');
        expect(api.mutations.single.$2, {
          'cargo_mode': 'sea',
          'container_id': 'container-42',
          'destination_city': 'Arusha',
          'destination_country': 'Tanzania',
        });
        expect(find.text('SUPPLIER MARK'), findsOneWidget);
        final confirm = find.text('Confirm cargo booking');
        await tester.ensureVisible(confirm);
        await tester.tap(confirm, warnIfMissed: false);
        await tester.pumpAndSettle();
        expect(api.mutations, hasLength(2));
        final booking = api.mutations.last;
        expect(
          booking.$1,
          account == BookingAccount.customer
              ? 'customer/sea-bookings'
              : 'sourcing_agent/containers/book-cbm',
        );
        expect(booking.$2, {
          'container_id': 'container-42',
          'destination_country': 'Tanzania',
          if (account == BookingAccount.customer)
            'booked_cbm': 2.5
          else
            'cbm_amount': 2.5,
          if (account == BookingAccount.customer)
            'destination_region': 'Arusha'
          else
            'destination_city': 'Arusha',
        });
        expect(find.text('Cargo space booked'), findsOneWidget);
        expect(find.text('TRACK-42'), findsOneWidget);
        expect(tester.takeException(), isNull);
      },
    );
  }
  testWidgets(
    'invalid nonfinite volume cannot prepare an address or book cargo',
    (tester) async {
      FlutterSecureStorage.setMockInitialValues({});
      final api = _BookingApi(TokenStorage());
      await tester.pumpWidget(
        ProviderScope(
          overrides: [apiClientProvider.overrideWithValue(api)],
          child: MaterialApp(
            theme: operationalTheme,
            home: const GuidedSeaBookingPage(
              account: BookingAccount.customer,
              initialContainerId: 'container-42',
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Cargo volume (CBM)'),
        'NaN',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Destination city'),
        'Arusha',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Destination country'),
        'Tanzania',
      );
      final review = find.text('Review cargo booking');
      await tester.ensureVisible(review);
      await tester.tap(review, warnIfMissed: false);
      await tester.pumpAndSettle();
      expect(api.mutations, isEmpty);
      expect(find.text('Enter a volume greater than zero.'), findsOneWidget);
    },
  );
}

class _BookingApi extends ApiClient {
  _BookingApi(TokenStorage storage)
    : super(
        tokenStorage: storage,
        workspaceProvider: WorkspaceProvider(storage),
        enableLogging: false,
      );
  final mutations = <(String, Map<String, dynamic>)>[];
  @override
  Future<T> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    expect(
      queryParameters,
      isNull,
      reason: 'Container APIs return a list and do not implement search/page parameters.',
    );
    return <Map<String, dynamic>>[
      {
        'id': 'container-42',
        'status': 'open',
        'available_cbm': 20,
        'operator': 'Cargo Company',
        'origin': 'Guangzhou',
        'destination': 'Dar es Salaam',
        'destination_country': 'Tanzania',
        'price_per_cbm': 100,
        'currency': 'USD',
      },
    ] as T;
  }

  @override
  Future<T> post<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    mutations.add((path, Map<String, dynamic>.from(data as Map)));
    return (path == 'forwarding/prepare-address'
            ? {
                'id': 'address-42',
                'shipping_mark': 'MARK',
                'copy': {'shipping_mark': 'SUPPLIER MARK'},
              }
            : {
                'sea_booking_id': 'booking-42',
                'tracking_number': 'TRACK-42',
                'cbm_booked': 2.5,
                'payment_status': 'pending',
                'logistics_charge': 250,
                'currency': 'USD',
              })
        as T;
  }
}
