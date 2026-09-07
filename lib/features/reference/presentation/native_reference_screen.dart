import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../app/app_route_aliases.dart';
import '../../../core/ui/logistics_ui.dart';
import '../../../core/ui/sahajomy_ui.dart';
import '../../public_services/presentation/official_information_page.dart';
import 'native_screen_specs.dart';

/// Informational destinations use the official website; transactional screens
/// are implemented by dedicated pages and never simulate a successful action.
class PreviewPageLayout extends StatelessWidget {
  const PreviewPageLayout({required this.spec, super.key});
  final NativeScreenSpec spec;
  @override
  Widget build(BuildContext context) {
    final aliases = appRouteAliases.entries.where((e) => e.value == spec.fileName && !e.key.contains(':'));
    final path = aliases.isEmpty ? '/contact' : aliases.first.key;
    final title = spec.fileName == 'public-terms.html' ? 'Terms of Service'
        : spec.fileName == 'public-privacy.html' ? 'Privacy Policy' : spec.title;
    return OfficialInformationPage(title: title, path: path);
  }
}

class NativeScreenCatalog extends StatelessWidget {
  const NativeScreenCatalog({super.key});
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(title: 'Screen review'),
    body: ListView.builder(
      padding: const EdgeInsets.all(24),
      itemCount: nativeScreenSpecs.length + 1,
      itemBuilder: (context, index) {
        if (index == 0) return const LogisticsIntro(title: 'Screen review', description: 'Review native customer, sourcing and cargo operations screens.');
        final spec = nativeScreenSpecs[index - 1];
        return ListTile(title: Text(spec.title), subtitle: Text(spec.role),
          trailing: const Icon(Icons.chevron_right_rounded), onTap: () => context.push(spec.routeName));
      },
    ),
  );
}
