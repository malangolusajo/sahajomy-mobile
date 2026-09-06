import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class FeatureMenuEntry {
  const FeatureMenuEntry({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.route,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final String route;
}

class FeatureMenuPage extends StatelessWidget {
  const FeatureMenuPage({
    required this.title,
    required this.description,
    required this.entries,
    super.key,
  });

  final String title;
  final String description;
  final List<FeatureMenuEntry> entries;

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
    children: [
      Text(title, style: Theme.of(context).textTheme.headlineMedium),
      const SizedBox(height: 6),
      Text(description),
      const SizedBox(height: 20),
      for (final entry in entries)
        Card(
          margin: const EdgeInsets.only(bottom: 10),
          child: ListTile(
            minTileHeight: 64,
            contentPadding: const EdgeInsets.symmetric(
              horizontal: 16,
              vertical: 6,
            ),
            leading: Icon(
              entry.icon,
              color: Theme.of(context).colorScheme.primary,
            ),
            title: Text(
              entry.title,
              style: const TextStyle(fontWeight: FontWeight.w800),
            ),
            subtitle: Text(entry.subtitle),
            trailing: const Icon(Icons.chevron_right_rounded),
            onTap: () => context.push(entry.route),
          ),
        ),
    ],
  );
}
