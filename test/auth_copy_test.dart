import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sahajomy_mobile/app/theme.dart';
import 'package:sahajomy_mobile/core/providers.dart';
import 'package:sahajomy_mobile/features/auth/presentation/otp_page.dart';
import 'package:sahajomy_mobile/features/auth/presentation/registration_page.dart';
import 'package:sahajomy_mobile/features/auth/presentation/sign_in_page.dart';

void main() {
  testWidgets('new customer link opens the registration form', (tester) async {
    final router = GoRouter(
      initialLocation: '/sign-in',
      routes: [
        GoRoute(path: '/sign-in', builder: (_, _) => const SignInPage()),
        GoRoute(path: '/register', builder: (_, _) => const RegistrationPage()),
      ],
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp.router(theme: sahajomyTheme, routerConfig: router),
      ),
    );

    expect(find.text('Email me a verification code'), findsOneWidget);
    expect(find.textContaining('registered email address'), findsOneWidget);
    expect(find.text('New to Sahajomy? Create an account'), findsOneWidget);
    expect(find.textContaining('mobile verification'), findsNothing);

    await tester.tap(find.text('New to Sahajomy? Create an account'));
    await tester.pumpAndSettle();

    expect(find.text('Create your Sahajomy account'), findsOneWidget);
    expect(find.text('Email address'), findsOneWidget);
    expect(find.text('Email my verification code'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('verification screen describes email delivery', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          pendingPhoneNumberProvider.overrideWith((ref) => '+255712345678'),
          pendingEmailProvider.overrideWith((ref) => 'amina@example.com'),
        ],
        child: MaterialApp(theme: sahajomyTheme, home: const OtpPage()),
      ),
    );

    expect(find.text('Check your email'), findsOneWidget);
    expect(find.text('Enter the code from your email'), findsOneWidget);
    expect(
      find.text('We sent a six-digit code to amina@example.com.'),
      findsOneWidget,
    );
    expect(find.text('Resend code by email'), findsNothing);
    expect(tester.takeException(), isNull);
  });
}
