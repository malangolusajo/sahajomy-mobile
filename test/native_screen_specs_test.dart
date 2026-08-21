import 'package:flutter_test/flutter_test.dart';
import 'package:sahajomy_mobile/features/reference/presentation/native_screen_specs.dart';

void main() {
  test('registers every approved mobile screen', () {
    expect(nativeScreenSpecs, hasLength(104));
    expect(
      nativeScreenSpecs.map((screen) => screen.routeName).toSet(),
      hasLength(104),
    );
  });
}
