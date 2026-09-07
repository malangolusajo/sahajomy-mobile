import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'router.dart';
import 'operational_theme.dart';

void runSahajomyApp() => runApp(const ProviderScope(child: SahajomyApp()));

class SahajomyApp extends ConsumerWidget {
  const SahajomyApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    return MaterialApp.router(
      title: 'Sahajomy',
      debugShowCheckedModeBanner: false,
      theme: operationalTheme,
      routerConfig: router,
    );
  }
}
