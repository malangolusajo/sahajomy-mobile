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

    expect(
      find.text('Find it in China. We’ll help you bring it home.'),
      findsOneWidget,
    );
    expect(find.text('Agizisha marketplace'), findsOneWidget);
    expect(find.text('Sourcing support'), findsWidgets);
    expect(find.text('SAHAJOMY'), findsNothing);
    expect(find.text('PUBLIC'), findsNothing);
    expect(find.text('CUSTOMER'), findsNothing);
    expect(tester.takeException(), isNull);

    await tester.drag(find.byType(PageView), const Offset(-350, 0));
    await tester.pumpAndSettle();
    expect(
      find.text('Small parcel or full container—it’s your call.'),
      findsOneWidget,
    );
    expect(find.text('Sea freight'), findsWidgets);
    expect(find.text('Express Air Cargo'), findsOneWidget);
    expect(tester.takeException(), isNull);

    await tester.drag(find.byType(PageView), const Offset(-350, 0));
    await tester.pumpAndSettle();
    expect(
      find.text('Know what’s happening without chasing updates.'),
      findsOneWidget,
    );
    expect(find.text('Documents & packing lists'), findsOneWidget);
    expect(find.text('Status alerts'), findsOneWidget);
    expect(find.text('SAHAJOMY'), findsNothing);
    expect(tester.takeException(), isNull);

    await tester.drag(find.byType(PageView), const Offset(-350, 0));
    await tester.pumpAndSettle();
    expect(
      find.text('Your parcels are ready. Pickup stays simple.'),
      findsOneWidget,
    );
    expect(find.text('Warehouse parcels'), findsOneWidget);
    expect(find.text('Multi-parcel requests'), findsOneWidget);
    expect(find.text('Secure QR & PIN'), findsOneWidget);
    expect(find.text('Get started'), findsOneWidget);
    expect(find.text('SAHAJOMY'), findsNothing);
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
