import 'package:flutter/material.dart';

import '../../../../core/ui/sahajomy_ui.dart';
import '../../batches/data/sourcing_agent_batches_repository.dart';

class SourcingAgentNotificationsPage extends StatefulWidget {
  const SourcingAgentNotificationsPage({super.key});

  @override
  State<SourcingAgentNotificationsPage> createState() =>
      _SourcingAgentNotificationsPageState();
}

class _SourcingAgentNotificationsPageState
    extends State<SourcingAgentNotificationsPage> {
  final _repository = SourcingAgentBatchesRepository();
  late Future<Map<String, dynamic>> _batches = _repository.listBatches();

  void _retry() => setState(() => _batches = _repository.listBatches());

  @override
  Widget build(BuildContext context) => FutureBuilder<Map<String, dynamic>>(
    future: _batches,
    builder: (context, snapshot) {
      if (snapshot.connectionState != ConnectionState.done) {
        return const Center(child: CircularProgressIndicator());
      }
      if (snapshot.hasError) {
        return SahajomyMessageState(
          icon: Icons.wifi_off_rounded,
          message: 'Batch activity is unavailable right now.',
          actionLabel: 'Try again',
          onAction: _retry,
        );
      }

      final batches = (snapshot.data!['batches'] as List? ?? const [])
          .cast<Map<String, dynamic>>();
      final events = <Map<String, String>>[
        for (final batch in batches.take(6))
          {
            'title': batch['title'] as String? ?? 'Batch updated',
            'message':
                '${batch['total_orders'] ?? 0} orders • ${batch['status'] ?? 'Draft'} • ${batch['shipping_method'] ?? 'Shipping'}',
            'badge': '${batch['status'] ?? 'Live'}',
          },
      ];

      return ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            'Batch activity',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 6),
          const Text(
            'Important sourcing changes and workflow reminders in one place.',
          ),
          const SizedBox(height: 20),
          if (events.isEmpty)
            const SahajomySectionCard(
              title: 'No activity yet',
              children: [
                Text(
                  'Batch alerts will appear here as soon as you start creating sourcing work.',
                ),
              ],
            ),
          if (events.isNotEmpty)
            Container(
              decoration: const BoxDecoration(
                color: Colors.white,
                border: Border.symmetric(
                  vertical: BorderSide(color: Color(0xFFE2E8F0)),
                ),
              ),
              child: Column(
                children: [
                  for (final event in events)
                    SahajomyPreviewRow(
                      title: event['title']!,
                      subtitle: event['message']!,
                      icon: Icons.notifications_none_rounded,
                      trailing: SahajomyStatusPill(label: event['badge']!),
                    ),
                ],
              ),
            ),
          const SizedBox(height: 18),
          FilledButton(
            onPressed: events.isEmpty
                ? null
                : () => ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('All activity marked as read.'),
                    ),
                  ),
            child: const Text('Mark all as read'),
          ),
        ],
      );
    },
  );
}
