import 'package:flutter/material.dart';

import '../../../../core/ui/sahajomy_ui.dart';
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
    appBar: const SahajomyScreenHeader(
      role: 'Customer',
      title: 'Track shipment',
    ),
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
        final first = events.first;
        final progress = first['progress'];
        final progressValue = progress is num
            ? progress.clamp(0, 100) / 100
            : .6;
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
          children: [
            Text(
              'Shipment progress',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 6),
            const Text(
              'Follow your container from departure to delivery with the latest logistics updates.',
            ),
            const SizedBox(height: 20),
            _ShipmentBanner(event: first, progress: progressValue),
            const SizedBox(height: 20),
            for (final event in events) _TrackingEventCard(event: event),
            const SizedBox(height: 20),
            FilledButton(
              onPressed: () {},
              child: const Text('View shipment details'),
            ),
          ],
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
    final stage =
        event['stage_label'] as String? ??
        event['event_type'] as String? ??
        'Tracking update';
    return Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const CircleAvatar(
            radius: 14,
            backgroundColor: Color(0xFFFFEEE9),
            child: Icon(Icons.circle, size: 10, color: Color(0xFFE85A3A)),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  stage,
                  style: const TextStyle(fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 3),
                Text(
                  event['description'] as String? ??
                      _formatTimestamp(event['timestamp'] as String?),
                  style: const TextStyle(fontSize: 12),
                ),
              ],
            ),
          ),
        ],
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

class _ShipmentBanner extends StatelessWidget {
  const _ShipmentBanner({required this.event, required this.progress});
  final Map<String, dynamic> event;
  final double progress;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(20),
    decoration: BoxDecoration(
      color: const Color(0xFF0F3D5E),
      borderRadius: BorderRadius.circular(16),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'CONTAINER',
          style: TextStyle(
            color: Color(0xFFBFDBFE),
            fontSize: 12,
            fontWeight: FontWeight.w800,
            letterSpacing: 1,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          '${event['display_reference'] ?? 'Sahajomy shipment'}',
          style: const TextStyle(
            color: Colors.white,
            fontSize: 20,
            fontWeight: FontWeight.w800,
          ),
        ),
        const SizedBox(height: 18),
        const Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Origin',
              style: TextStyle(color: Colors.white70, fontSize: 12),
            ),
            Text(
              'In transit',
              style: TextStyle(
                color: Color(0xFFFFB5A4),
                fontSize: 12,
                fontWeight: FontWeight.w800,
              ),
            ),
            Text(
              'Destination',
              style: TextStyle(color: Colors.white70, fontSize: 12),
            ),
          ],
        ),
        const SizedBox(height: 8),
        LinearProgressIndicator(
          value: progress,
          minHeight: 6,
          borderRadius: BorderRadius.circular(10),
          backgroundColor: Colors.white24,
          color: const Color(0xFFFF6B4A),
        ),
      ],
    ),
  );
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
