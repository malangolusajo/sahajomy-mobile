import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/ui/logistics_ui.dart';
import '../../../core/ui/sahajomy_ui.dart';

Future<void> openSahajomyPage(BuildContext context, String path) async {
  final uri = Uri.https('sahajomy.co.tz', path);
  try {
    if (await launchUrl(uri, mode: LaunchMode.externalApplication)) return;
  } catch (_) { /* Offer a readable URL when the device has no browser. */ }
  if (context.mounted) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Open ${uri.toString()} in your browser.')));
  }
}

class OfficialInformationPage extends StatelessWidget {
  const OfficialInformationPage({required this.title, required this.path, this.description, super.key});
  final String title;
  final String path;
  final String? description;
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: SahajomyScreenHeader(title: title),
    body: ListView(padding: const EdgeInsets.all(24), children: [
      const Align(alignment: Alignment.centerLeft, child: SahajomyBrandMark(size: 56, showShadow: false)),
      const SizedBox(height: 28),
      LogisticsIntro(eyebrow: 'Sahajomy', title: title, description: description ?? 'Read the current $title on the official Sahajomy website.'),
      FilledButton.icon(onPressed: () => openSahajomyPage(context, path), icon: const Icon(Icons.open_in_new_rounded), label: Text('Read $title')),
      const SizedBox(height: 16),
      SelectableText('https://sahajomy.co.tz$path'),
      const SizedBox(height: 32),
      const Divider(),
      ListTile(contentPadding: EdgeInsets.zero, title: const Text('Privacy Policy'), trailing: const Icon(Icons.north_east_rounded), onTap: () => openSahajomyPage(context, '/privacy')),
      ListTile(contentPadding: EdgeInsets.zero, title: const Text('Terms of Service'), trailing: const Icon(Icons.north_east_rounded), onTap: () => openSahajomyPage(context, '/terms')),
    ]),
  );
}

class SahajomyLegalLinks extends StatelessWidget {
  const SahajomyLegalLinks({super.key});
  @override
  Widget build(BuildContext context) => Wrap(alignment: WrapAlignment.center, spacing: 12, children: [
    TextButton(onPressed: () => openSahajomyPage(context, '/terms'), child: const Text('Terms of Service')),
    TextButton(onPressed: () => openSahajomyPage(context, '/privacy'), child: const Text('Privacy Policy')),
  ]);
}
