import 'package:flutter_test/flutter_test.dart';
import 'package:sahajomy_mobile/app/app.dart';

void main() {
  testWidgets('shows the Sahajomy welcome experience', (tester) async {
    await tester.pumpWidget(const SahajomyApp());

    expect(find.text('Sahajomy'), findsOneWidget);
    expect(find.text('Sign in with phone number'), findsOneWidget);
  });
}
