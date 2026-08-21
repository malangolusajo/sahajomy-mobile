import 'package:flutter/material.dart';

import '../data/customer_tracking_repository.dart';

class ShipmentTrackingPage extends StatefulWidget {
  const ShipmentTrackingPage({super.key});

  @override
  State<ShipmentTrackingPage> createState() => _ShipmentTrackingPageState();
}

class _ShipmentTrackingPageState extends State<ShipmentTrackingPage> {
  final _repository = CustomerTrackingRepository();
  late Future<List<Map<String, dynamic>>> _events = _repository.listEvents();

  void _retry() => setState(() => _events = _repository.listEvents());

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Track shipment')),
    body: FutureBuilder<List<Map<String, dynamic>>>(
      future: _events,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return _TrackingMessage(
            message: 'We could not load your tracking updates.',
            actionLabel: 'Try again',
            onAction: _retry,
          );
        }
        final events = snapshot.data ?? [];
        if (events.isEmpty) {
          return const _TrackingMessage(
            message: 'Tracking updates will appear here once your cargo starts moving.',
          );
        }
        return ListView.separated(
          padding: const EdgeInsets.all(20),
          itemCount: events.length,
          separatorBuilder: (_, _) => const SizedBox(height: 12),
          itemBuilder: (_, index) => _TrackingEventCard(event: events[index]),
        );
      },
    ),
  );
}

class _TrackingEventCard extends StatelessWidget {
  const _TrackingEventCard({required this.event});

  final Map<String, dynamic> event;

  @override
  Widget build(BuildContext context) {
    final progress = event['progress'];
    final progressValue = progress is num ? progress.clamp(0, 100) / 100 : null;
    final stage =
        event['stage_label'] as String? ??
        event['event_type'] as String? ??
        'Tracking update';
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.local_shipping_outlined,
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    stage,
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                ),
                Text(_formatTimestamp(event['timestamp'] as String?)),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              event['description'] as String? ?? 'Your shipment was updated.',
            ),
            if (progressValue != null) ...[
              const SizedBox(height: 12),
              LinearProgressIndicator(value: progressValue),
            ],
            const SizedBox(height: 10),
            Text(
              event['display_reference'] as String? ?? 'Sahajomy shipment',
              style: Theme.of(context).textTheme.labelMedium,
            ),
          ],
        ),
      ),
    );
  }

  String _formatTimestamp(String? value) {
    if (value == null || value.isEmpty) return 'Recent';
    final parsed = DateTime.tryParse(value);
    if (parsed == null) return value;
    return '${parsed.year}-${parsed.month.toString().padLeft(2, '0')}-${parsed.day.toString().padLeft(2, '0')}';
  }
}

class _TrackingMessage extends StatelessWidget {
  const _TrackingMessage({
    required this.message,
    this.actionLabel,
    this.onAction,
  });

  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.route_outlined, size: 44),
          const SizedBox(height: 14),
          Text(message, textAlign: TextAlign.center),
          if (onAction != null) ...[
            const SizedBox(height: 16),
            OutlinedButton(onPressed: onAction, child: Text(actionLabel!)),
          ],
        ],
      ),
    ),
  );
}
