import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sahajomy_mobile/app/theme.dart';
import 'package:sahajomy_mobile/core/ui/sahajomy_ui.dart';
import 'package:sahajomy_mobile/features/onboarding/presentation/onboarding_page.dart';

void main() {
  testWidgets('onboarding presents polished benefit-led content', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(theme: sahajomyTheme, home: const OnboardingPage()),
      ),
    );

    expect(find.text('Move cargo with confidence'), findsOneWidget);
    expect(find.text('SAHAJOMY'), findsOneWidget);
    expect(find.text('PUBLIC'), findsNothing);
    expect(find.text('CUSTOMER'), findsNothing);
    expect(tester.takeException(), isNull);

    await tester.drag(find.byType(PageView), const Offset(-350, 0));
    await tester.pumpAndSettle();
    expect(find.text('Know where every shipment stands'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('public headers use the customer-facing Sahajomy label', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: sahajomyTheme,
        home: const Scaffold(
          appBar: SahajomyScreenHeader(role: 'Public', title: 'Services'),
        ),
      ),
    );

    expect(find.text('SAHAJOMY'), findsOneWidget);
    expect(find.text('PUBLIC'), findsNothing);
  });
}
