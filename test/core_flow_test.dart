import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sahajomy_mobile/app/operational_theme.dart';
import 'package:sahajomy_mobile/core/network/api_client.dart';
import 'package:sahajomy_mobile/core/network/api_exception.dart';
import 'package:sahajomy_mobile/core/providers.dart';
import 'package:sahajomy_mobile/core/storage/secure_storage.dart';
import 'package:sahajomy_mobile/features/auth/domain/otp_delivery.dart';
import 'package:sahajomy_mobile/features/auth/presentation/auth_status_page.dart';
import 'package:sahajomy_mobile/features/auth/presentation/otp_page.dart';
import 'package:sahajomy_mobile/features/auth/presentation/registration_page.dart';
import 'package:sahajomy_mobile/features/auth/presentation/sign_in_page.dart';
import 'package:sahajomy_mobile/features/auth/presentation/stay_updated_page.dart';
import 'package:sahajomy_mobile/features/onboarding/presentation/splash_page.dart';
import 'package:sahajomy_mobile/features/workspaces/presentation/branch_selection_page.dart';
import 'package:sahajomy_mobile/features/workspaces/presentation/checking_workspace_page.dart';
import 'package:sahajomy_mobile/features/workspaces/presentation/workspace_selection_page.dart';
import 'package:sahajomy_mobile/features/workspaces/data/workspace_repository.dart';

const _routes = <String, Widget>{
  '/splash': SplashPage(),
  '/sign-in': SignInPage(),
  '/register': RegistrationPage(),
  '/otp': OtpPage(),
  '/code-expired': AuthStatusPage(),
  '/account-suspended': AuthStatusPage(suspended: true),
  '/stay-updated': StayUpdatedPage(),
  '/account/workspaces': WorkspaceSelectionPage(),
  '/account/branches': BranchSelectionPage(),
  '/checking-workspace': CheckingWorkspacePage(),
};

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() async {
    const fontDir = String.fromEnvironment('CORE_FONT_DIR');
    if (fontDir.isNotEmpty) {
      final loader = FontLoader('Roboto');
      for (final name in ['roboto-regular.ttf', 'roboto-bold.ttf']) {
        loader.addFont(
          File('$fontDir/$name')
              .readAsBytes()
              .then((bytes) => ByteData.sublistView(bytes)),
        );
      }
      await loader.load();
      // Flutter's test binding forces Ahem on some control styles. Replace
      // that test-only font when exporting human-readable review renders.
      final testFont = FontLoader('Ahem');
      testFont.addFont(
        File('$fontDir/roboto-regular.ttf')
            .readAsBytes()
            .then((bytes) => ByteData.sublistView(bytes)),
      );
      await testFont.load();
      final icons = FontLoader('MaterialIcons');
      icons.addFont(
        File('$fontDir/MaterialIcons-Regular.otf')
            .readAsBytes()
            .then((bytes) => ByteData.sublistView(bytes)),
      );
      await icons.load();
    }
  });

  testWidgets(
    'new phone → registration → OTP → permission → company → branch → verified home',
    (tester) async {
      final h = await _mount(tester, '/sign-in');
      h.backend.newUser = true;
      await tester.enterText(find.byType(TextFormField), '+255712345678');
      await _tap(tester, 'Continue');
      expect(find.text('Create your account'), findsNWidgets(2));
      expect(find.text('+255712345678'), findsOneWidget);
      await tester.enterText(find.byType(TextFormField).at(0), 'Test Customer');
      await tester.enterText(
        find.byType(TextFormField).at(1),
        'customer@example.test',
      );
      await _tap(tester, 'Send verification code');
      expect(find.textContaining('c***@example.test'), findsOneWidget);
      final send = h.backend.requests
          .where((r) => r.path == 'auth/send-otp')
          .last;
      expect(send.data, {
        'phone_number': '+255712345678',
        'name': 'Test Customer',
        'email': 'customer@example.test',
      });
      expect(send.headers['Authorization'], isNull);
      await tester.enterText(find.byType(TextField), '123456');
      await _tap(tester, 'Verify & continue');
      expect(find.text('Allow notifications'), findsOneWidget);
      tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
        const MethodChannel('com.sahajomy.mobile/notifications'),
        (call) async => 'denied',
      );
      addTearDown(
        () => tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
          const MethodChannel('com.sahajomy.mobile/notifications'),
          null,
        ),
      );
      await _tap(tester, 'Allow notifications');
      expect(find.textContaining('Notifications are disabled'), findsOneWidget);
      await _tap(tester, 'Not now');
      await _tap(tester, 'Test Cargo Company');
      await _tap(tester, 'Continue');
      await _tap(tester, 'Guangzhou');
      await _tap(tester, 'Continue');
      expect(find.text('Verified home'), findsOneWidget);
      expect(h.container.read(workspaceProvider).branchId, 'branch-2');
      expect(
        h.backend.requests
            .lastWhere((r) => r.path == 'workspaces/roles')
            .headers['X-Sahajomy-Branch'],
        'branch-2',
      );
      expect(
        h.backend.requests.where(
          (r) => r.method == 'POST' && r.path == 'auth/verify-otp',
        ),
        hasLength(1),
      );
      await h.dispose(tester);
    },
  );

  for (final status in [400, 410, 403, 429, 503]) {
    testWidgets('OTP handles backend $status without saving a session', (
      tester,
    ) async {
      final h = await _mount(tester, '/otp');
      h.backend.verifyStatus = status;
      await tester.enterText(find.byType(TextField), '123456');
      await _tap(tester, 'Verify & continue');
      expect(h.router.routeInformationProvider.value.uri.path, switch (status) {
        410 => '/code-expired',
        403 => '/account-suspended',
        _ => '/otp',
      });
      expect(await h.container.read(sessionStoreProvider).read(), isNull);
      if (status == 400) {
        expect(
          find.textContaining('code you entered is incorrect'),
          findsOneWidget,
        );
      }
      if (status == 410) {
        await _tap(tester, 'Request new code');
        expect(h.router.routeInformationProvider.value.uri.path, '/otp');
        expect(
          h.container.read(pendingOtpDeliveryProvider)?.expiresAt,
          isNotNull,
        );
      }
      await h.dispose(tester);
    });
  }

  testWidgets(
    'slow verification cannot submit twice and retains invalid code',
    (tester) async {
      final h = await _mount(tester, '/otp');
      h.backend.verifyGate = Completer<void>();
      h.backend.verifyStatus = 400;
      await tester.enterText(find.byType(TextField), '123456');
      await tester.tap(find.text('Verify & continue'));
      await tester.pump();
      expect(
        tester.widget<FilledButton>(find.byType(FilledButton)).onPressed,
        isNull,
      );
      await tester.testTextInput.receiveAction(TextInputAction.done);
      await tester.pumpAndSettle();
      expect(
        h.backend.requests.where((r) => r.path == 'auth/verify-otp'),
        hasLength(1),
      );
      h.backend.verifyGate!.complete();
      await tester.pumpAndSettle();
      expect(find.text('123456'), findsOneWidget);
      await h.dispose(tester);
    },
  );

  testWidgets(
    'workspace loading, offline retry, personal-only and back navigation',
    (tester) async {
      final h = await _mount(
        tester,
        '/account/workspaces',
        authenticated: true,
        workspaceFailure: true,
      );
      expect(find.textContaining('Unable to connect'), findsOneWidget);
      h.backend.workspaceFailure = false;
      h.backend.noCompanies = true;
      await _tap(tester, 'Try again');
      expect(find.text('My Sahajomy Account'), findsOneWidget);
      expect(find.text('Test Cargo Company'), findsNothing);
      await _tap(tester, 'My Sahajomy Account');
      await _tap(tester, 'Continue');
      expect(find.text('Verified home'), findsOneWidget);
      expect(h.container.read(workspaceProvider).hasCompany, isFalse);
      await h.dispose(tester);
    },
  );

  testWidgets(
    'non-manager sees assigned branch without fetching privileged branch list',
    (tester) async {
      final h = await _mount(
        tester,
        '/account/branches',
        authenticated: true,
        manager: false,
      );
      expect(find.text('Yiwu'), findsOneWidget);
      expect(
        h.backend.requests.any((r) => r.path == 'workspaces/branches'),
        isFalse,
      );
      await tester.tap(find.byTooltip('Back'));
      await tester.pumpAndSettle();
      expect(find.text('Switch workspace'), findsOneWidget);
      await h.dispose(tester);
    },
  );

  testWidgets('expired local delivery moves to recovery using server expiry', (
    tester,
  ) async {
    final h = await _mount(tester, '/otp');
    h.container.read(pendingOtpDeliveryProvider.notifier).state = OtpDelivery(
      expiresAt: DateTime.now().subtract(const Duration(seconds: 1)),
    );
    await tester.pump(const Duration(seconds: 1));
    await tester.pumpAndSettle();
    expect(find.text('Code expired'), findsNWidgets(2));
    await h.dispose(tester);
  });

  testWidgets('checking restores an authorized booking deep link', (
    tester,
  ) async {
    final h = await _mount(
      tester,
      '/checking-workspace',
      authenticated: true,
      holdCheck: true,
      settle: false,
    );
    h.container.read(pendingDestinationProvider.notifier).state =
        '/customer/bookings/booking-42';
    h.backend.profileGate!.complete();
    await tester.pumpAndSettle();
    expect(
      h.router.routeInformationProvider.value.uri.path,
      '/customer/bookings/booking-42',
    );
    expect(find.text('Preserved booking'), findsOneWidget);
    await h.dispose(tester);
  });

  test(
    'typed list endpoint preserves 403 instead of throwing a JSON type error',
    () async {
      FlutterSecureStorage.setMockInitialValues({});
      final backend = _Backend()..rolesForbidden = true;
      final container = _container(backend);
      addTearDown(container.dispose);
      await expectLater(
        container.read(workspaceRepositoryProvider).verifyContext(),
        throwsA(isA<ApiException>().having((e) => e.statusCode, 'status', 403)),
      );
    },
  );

  for (final size in [
    const Size(320, 568),
    const Size(360, 800),
    const Size(390, 844),
    const Size(430, 932),
  ]) {
    for (final scale in [1.0, 2.0]) {
      testWidgets('all ten layouts fit ${size.width} at ${scale}x text', (
        tester,
      ) async {
        for (final path in _routes.keys) {
          final h = await _mount(
            tester,
            path,
            authenticated:
                path.startsWith('/account/') || path == '/checking-workspace',
            size: size,
            scale: scale,
            holdCheck: path == '/checking-workspace',
            settle: path != '/checking-workspace' && path != '/splash',
          );
          expect(tester.takeException(), isNull, reason: path);
          if (path != '/splash') {
            final headers = find.descendant(
              of: find.byType(AppBar),
              matching: find.text('SAHAJOMY'),
            );
            expect(headers, findsNothing);
          }
          const capture = bool.fromEnvironment('CAPTURE_CORE');
          if (capture && size.width == 390 && scale == 1) {
            await tester.pump(const Duration(milliseconds: 50));
            final boundary = tester.renderObject<RenderRepaintBoundary>(
              find.byKey(const ValueKey('capture')),
            );
            await tester.runAsync(() async {
              final image = await boundary.toImage(pixelRatio: 1);
              final bytes = await image.toByteData(
                format: ui.ImageByteFormat.png,
              );
              final directory = Directory('build/core-screen-review');
              await directory.create(recursive: true);
              await File(
                '${directory.path}/${path.substring(1).replaceAll('/', '-')}.png',
              ).writeAsBytes(bytes!.buffer.asUint8List());
              image.dispose();
            });
          }
          if (path == '/register') {
            await tester.scrollUntilVisible(
              find.text('Full name'),
              150,
              scrollable: find.byType(Scrollable).first,
            );
            await tester.ensureVisible(find.byType(TextFormField).first);
            await tester.pumpAndSettle();
            await tester.tap(find.byType(TextFormField).first);
            tester.view.viewInsets = const FakeViewPadding(bottom: 280);
            await tester.pump();
            await tester.scrollUntilVisible(
              find.text('Send verification code'),
              150,
              scrollable: find.byType(Scrollable).first,
            );
            expect(tester.takeException(), isNull);
            tester.view.resetViewInsets();
          }
          await h.dispose(tester);
        }
      });
    }
  }
}

Future<void> _tap(WidgetTester tester, String text) async {
  FocusManager.instance.primaryFocus?.unfocus();
  await tester.pumpAndSettle();
  await tester.ensureVisible(find.text(text));
  await tester.pumpAndSettle();
  await tester.tap(find.text(text));
  await tester.pumpAndSettle();
}

ProviderContainer _container(_Backend backend) => ProviderContainer(
  overrides: [
    apiClientProvider.overrideWith((ref) {
      final client = ApiClient(
        dio: Dio(BaseOptions(baseUrl: 'https://example.test/api/v1/'))
          ..httpClientAdapter = backend,
        tokenStorage: ref.watch(tokenStorageProvider),
        workspaceProvider: ref.watch(workspaceProvider.notifier),
        enableLogging: false,
      );
      ref.onDispose(client.close);
      return client;
    }),
  ],
);

Future<_Harness> _mount(
  WidgetTester tester,
  String path, {
  bool authenticated = false,
  bool manager = true,
  bool workspaceFailure = false,
  Size size = const Size(390, 844),
  double scale = 1,
  bool holdCheck = false,
  bool settle = true,
}) async {
  FlutterSecureStorage.setMockInitialValues({
    if (authenticated) ...{
      SecureStorage.accessTokenKey: 'test-access-token-123',
      SecureStorage.refreshTokenKey: 'test-refresh-token-123',
      SecureStorage.roleKey: 'customer',
      SecureStorage.companyIdKey: 'company-1',
      SecureStorage.branchIdKey: 'branch-1',
    },
  });
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  final backend = _Backend()
    ..manager = manager
    ..workspaceFailure = workspaceFailure;
  if (holdCheck) backend.profileGate = Completer<void>();
  final container = _container(backend);
  container.read(pendingPhoneNumberProvider.notifier).state = '+255712345678';
  final router = GoRouter(
    initialLocation: path,
    routes: [
      GoRoute(
        path: '/customer/bookings/booking-42',
        builder: (_, _) => const Scaffold(body: Text('Preserved booking')),
      ),
      for (final entry in _routes.entries)
        GoRoute(path: entry.key, builder: (_, _) => entry.value),
      for (final path in ['/customer', '/welcome', '/onboarding', '/mfa'])
        GoRoute(
          path: path,
          builder: (_, _) => const Scaffold(body: Text('Verified home')),
        ),
    ],
  );
  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: MaterialApp.router(
        theme: const String.fromEnvironment('CORE_FONT_DIR').isEmpty
            ? operationalTheme
            : operationalTheme.copyWith(
                textTheme: operationalTheme.textTheme.apply(
                  fontFamily: 'Roboto',
                ),
                primaryTextTheme: operationalTheme.primaryTextTheme.apply(
                  fontFamily: 'Roboto',
                ),
              ),
        routerConfig: router,
        builder: (context, child) => MediaQuery(
          data: MediaQuery.of(context)
              .copyWith(textScaler: TextScaler.linear(scale)),
          child: RepaintBoundary(key: const ValueKey('capture'), child: child!),
        ),
      ),
    ),
  );
  if (settle) {
    await tester.pumpAndSettle();
  } else {
    await tester.pump();
  }
  return _Harness(container, router, backend);
}

class _Harness {
  _Harness(this.container, this.router, this.backend);
  final ProviderContainer container;
  final GoRouter router;
  final _Backend backend;
  Future<void> dispose(WidgetTester tester) async {
    await tester.pumpWidget(const SizedBox());
    if (backend.profileGate case final gate? when !gate.isCompleted) {
      gate.complete();
      await tester.pump();
    }
    await tester.pump(const Duration(seconds: 2));
    router.dispose();
    container.dispose();
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
    tester.view.resetViewInsets();
  }
}

class _Backend implements HttpClientAdapter {
  final requests = <RequestOptions>[];
  bool newUser = false,
      noCompanies = false,
      manager = true,
      workspaceFailure = false,
      rolesForbidden = false;
  int verifyStatus = 200;
  Completer<void>? verifyGate, profileGate;
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);
    switch (options.path) {
      case 'auth/send-otp':
        if (newUser && (options.data as Map)['name'] == null) {
          return _json({
            'detail': 'Name and email are required for new user registration.',
          }, 400);
        }
        newUser = false;
        return _json({
          'masked_email': 'c***@example.test',
          'expires_in_minutes': 5,
        });
      case 'auth/verify-otp':
        await verifyGate?.future;
        if (verifyStatus != 200) {
          return _json({
            'detail': switch (verifyStatus) {
              400 => 'The code you entered is incorrect. Please try again.',
              403 => 'Account suspended. Contact support.',
              _ => 'error',
            },
          }, verifyStatus);
        }
        return _json({
          'access_token': 'test-access-token-123',
          'refresh_token': 'test-refresh-token-123',
        });
      case 'auth/me':
        await profileGate?.future;
        return _json({'role': 'customer', 'status': 'active'});
      case 'workspaces':
        if (workspaceFailure) {
          throw DioException(
            requestOptions: options,
            type: DioExceptionType.connectionError,
          );
        }
        return _json({
          'personal': {
            'id': 'personal',
            'type': 'personal',
            'name': 'My Sahajomy Account',
          },
          'companies': noCompanies
              ? []
              : [
                  {
                    'id': 'membership-1',
                    'type': 'cargo_company',
                    'company_id': 'company-1',
                    'company_name': 'Test Cargo Company',
                    'branch_id': 'branch-1',
                    'branch_name': 'Yiwu',
                    'role_id': 'role-1',
                    'role': 'Cargo Company Owner',
                    'status': 'active',
                    'permissions': [
                      if (manager) 'company.branch.manage',
                      'booking.view',
                    ],
                  },
                ],
        });
      case 'workspaces/roles':
        return rolesForbidden
            ? _json({'detail': 'Missing permission'}, 403)
            : _json([
                {'id': 'role-1', 'scope': manager ? 'company' : 'branch'},
              ]);
      case 'workspaces/branches':
        return _json([
          {
            'id': 'branch-1',
            'company_id': 'company-1',
            'name': 'Yiwu',
            'city': 'Yiwu',
            'country': 'China',
          },
          {
            'id': 'branch-2',
            'company_id': 'company-1',
            'name': 'Guangzhou',
            'city': 'Guangzhou',
            'country': 'China',
          },
        ]);
      default:
        return _json({'detail': 'Not found'}, 404);
    }
  }

  ResponseBody _json(Object body, [int status = 200]) =>
      ResponseBody.fromString(
        jsonEncode(body),
        status,
        headers: {
          Headers.contentTypeHeader: ['application/json'],
        },
      );
  @override
  void close({bool force = false}) {}
}
