import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:sahajomy_mobile/core/auth/session.dart';
import 'package:sahajomy_mobile/core/network/interceptors/logging_interceptor.dart';
import 'package:sahajomy_mobile/core/security/app_link_guard.dart';
import 'package:sahajomy_mobile/core/storage/secure_storage.dart';
import 'package:sahajomy_mobile/features/auth/domain/auth_input.dart';
import 'package:sahajomy_mobile/core/storage/token_storage.dart';
import 'package:sahajomy_mobile/core/workspaces/workspace_provider.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('sensitive log redaction', () {
    test('removes capability tokens and every query value', () {
      final safe = redactUriForLogging(
        Uri.parse(
          'https://sahajomy.co.tz/api/v1/public/batch/SUPER_SECRET_TOKEN_123?phone=%2B255700000000',
        ),
      );
      expect(safe, '/api/v1/public/batch/<redacted>');
      expect(safe, isNot(contains('SUPER_SECRET')));
      expect(safe, isNot(contains('255700')));
    });

    test('redacts warehouse and receipt credentials', () {
      expect(
        redactUriForLogging(
          Uri.parse('/customer/warehouse-access/a_secure_token_12345'),
        ),
        '/customer/warehouse-access/<redacted>',
      );
      expect(
        redactUriForLogging(Uri.parse('/public/receipt/verify/RECEIPT123')),
        '/public/receipt/verify/<redacted>',
      );
    });
  });

  group('app-link allowlist', () {
    test('accepts only a role-compatible protected destination', () {
      const token = 'abcdefghijklmnop_123456';
      expect(
        sanitizePendingDestination(
          '/customer/warehouse-access/$token',
          role: UserRole.customer,
        ),
        '/customer/warehouse-access/$token',
      );
      expect(
        sanitizePendingDestination(
          '/customer/warehouse-access/$token',
          role: UserRole.cargoAdmin,
        ),
        isNull,
      );
    });

    test(
      'rejects external, traversal, short-token, and public destinations',
      () {
        expect(
          sanitizePendingDestination('https://evil.test/customer'),
          isNull,
        );
        expect(sanitizePendingDestination('/customer/../admin/users'), isNull);
        expect(
          sanitizePendingDestination('/customer/warehouse-access/short'),
          isNull,
        );
        expect(sanitizePendingDestination('/public/containers'), isNull);
      },
    );
  });

  group('authentication input', () {
    test('normalizes E.164 phone numbers without putting them in a route', () {
      expect(normalizePhoneNumber('+255 712-345-678'), '+255712345678');
      expect(isValidPhoneNumber('+255 712-345-678'), isTrue);
      expect(isValidPhoneNumber('0712345678'), isFalse);
    });

    test('requires an exact six-digit OTP', () {
      expect(isValidOtp('123456'), isTrue);
      expect(isValidOtp('1234'), isFalse);
      expect(isValidOtp('12345a'), isFalse);
    });
  });

  test('workspace capability checks fail closed and switching invalidates responses', () async {
    FlutterSecureStorage.setMockInitialValues({});
    final workspace = WorkspaceProvider(TokenStorage());
    await workspace.ready;
    await workspace.setWorkspace(
      companyId: 'company-1',
      companyName: 'Cargo Co',
      permissions: const ['finance.read'],
    );
    expect(workspace.canOpenRoute('/cargo/finance'), isTrue);
    expect(workspace.canOpenRoute('/cargo/settings/staff-branches'), isFalse);
    final oldRevision = workspace.revision;
    await workspace.clearWorkspace();
    expect(workspace.revision, greaterThan(oldRevision));
    expect(workspace.state.hasCompany, isFalse);
  });

  test(
    'a redesigned onboarding version is shown once after an update',
    () async {
      FlutterSecureStorage.setMockInitialValues({
        SecureStorage.onboardingCompletedKey: 'true',
      });
      final storage = TokenStorage();

      expect(await storage.getOnboardingCompleted(), isFalse);
      await storage.setOnboardingCompleted();
      expect(await storage.getOnboardingCompleted(), isTrue);
    },
  );
}
