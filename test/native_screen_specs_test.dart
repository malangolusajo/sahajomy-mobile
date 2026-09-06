import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sahajomy_mobile/app/theme.dart';
import 'package:sahajomy_mobile/app/app_route_aliases.dart';
import 'package:sahajomy_mobile/core/network/api_client.dart';
import 'package:sahajomy_mobile/core/providers.dart';
import 'package:sahajomy_mobile/core/storage/token_storage.dart';
import 'package:sahajomy_mobile/core/workspaces/workspace_provider.dart';
import 'package:sahajomy_mobile/features/reference/presentation/dedicated_preview_pages.dart';
import 'package:sahajomy_mobile/features/reference/presentation/native_screen_specs.dart';

void main() {
  test('registers every approved mobile screen', () {
    expect(nativeScreenSpecs, hasLength(125));
    expect(
      nativeScreenSpecs.map((screen) => screen.routeName).toSet(),
      hasLength(125),
    );
  });

  test('matches the source-of-truth preview directory exactly', () {
    final sourceFiles =
        Directory('Sahajomy-Mobile-App/Sahajomy-Mobile-App/html-previews')
            .listSync()
            .whereType<File>()
            .map((file) => file.uri.pathSegments.last)
            .where((name) => name.endsWith('.html'))
            .toSet();
    final registeredFiles = nativeScreenSpecs
        .map((spec) => spec.fileName)
        .toSet();

    expect(registeredFiles, sourceFiles);
    expect(appRouteAliases.values.every(registeredFiles.contains), isTrue);
  });

  test('maps every preview to a distinct dedicated Flutter page class', () {
    final pageTypes = nativeScreenSpecs
        .map((spec) => dedicatedPreviewPageFor(spec).runtimeType)
        .toSet();

    expect(pageTypes, hasLength(125));
  });

  testWidgets('builds every approved screen as native Flutter UI', (
    tester,
  ) async {
    FlutterSecureStorage.setMockInitialValues({});
    final storage = TokenStorage();
    final api = _FakeApiClient(storage);
    for (final spec in nativeScreenSpecs) {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [apiClientProvider.overrideWithValue(api)],
          child: MaterialApp(
            theme: sahajomyTheme,
            home: dedicatedPreviewPageFor(spec),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull, reason: spec.fileName);
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pumpAndSettle();
    }
  });
}

class _FakeApiClient extends ApiClient {
  _FakeApiClient(TokenStorage storage)
    : super(
        tokenStorage: storage,
        workspaceProvider: WorkspaceProvider(storage),
        enableLogging: false,
      );

  @override
  Future<T> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async => <String, dynamic>{} as T;

  @override
  Future<List<Map<String, dynamic>>> getList(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async => const [];

  @override
  Future<Map<String, dynamic>> getObject(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async => const {};
}
