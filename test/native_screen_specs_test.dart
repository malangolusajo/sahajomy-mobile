import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sahajomy_mobile/app/theme.dart';
import 'package:sahajomy_mobile/features/reference/presentation/dedicated_preview_pages.dart';
import 'package:sahajomy_mobile/features/reference/presentation/native_screen_specs.dart';

void main() {
  test('registers every approved mobile screen', () {
    expect(nativeScreenSpecs, hasLength(104));
    expect(
      nativeScreenSpecs.map((screen) => screen.routeName).toSet(),
      hasLength(104),
    );
  });

  test('maps every preview to a distinct dedicated Flutter page class', () {
    final pageTypes = nativeScreenSpecs
        .map((spec) => dedicatedPreviewPageFor(spec).runtimeType)
        .toSet();

    expect(pageTypes, hasLength(104));
  });

  testWidgets('builds every approved screen as native Flutter UI', (
    tester,
  ) async {
    for (final spec in nativeScreenSpecs) {
      await tester.pumpWidget(
        MaterialApp(theme: sahajomyTheme, home: dedicatedPreviewPageFor(spec)),
      );
      await tester.pump();

      if (spec.fileName != 'public-containers.html') {
        expect(find.text(spec.title), findsAtLeastNWidgets(1));
      }
      expect(tester.takeException(), isNull, reason: spec.fileName);
    }
  });
}
