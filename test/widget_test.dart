import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';
import 'package:sahajomy_mobile/app/theme.dart';
import 'package:sahajomy_mobile/features/auth/presentation/welcome_page.dart';

void main() {
  testWidgets('shows the Sahajomy welcome experience', (tester) async {
    await tester.pumpWidget(
      MaterialApp(theme: sahajomyTheme, home: const WelcomePage()),
    );

    expect(find.text('SAHAJOMY'), findsOneWidget);
    expect(find.text('Get started'), findsOneWidget);
  });
}
