import 'package:flutter/material.dart';

import '../../../core/ui/sahajomy_ui.dart';
import '../data/workflow_api_repository.dart';

/// A live, read-only operation page for API workflows without a selected entity.
class LiveWorkflowPage extends StatefulWidget {
  const LiveWorkflowPage({
    required this.role,
    required this.title,
    required this.endpoint,
    this.description,
    super.key,
  });

  final String role;
  final String title;
  final String endpoint;
  final String? description;

  @override
  State<LiveWorkflowPage> createState() => _LiveWorkflowPageState();
}

class _LiveWorkflowPageState extends State<LiveWorkflowPage> {
  final _repository = WorkflowApiRepository();
  late Future<Object> _result = _repository.load(widget.endpoint);

  void _reload() => setState(() => _result = _repository.load(widget.endpoint));

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: SahajomyScreenHeader(role: widget.role, title: widget.title),
    body: FutureBuilder<Object>(
      future: _result,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return SahajomyMessageState(
            icon: Icons.cloud_off_outlined,
            message: 'We could not load ${widget.title.toLowerCase()}.',
            actionLabel: 'Try again',
            onAction: _reload,
          );
        }
        final records = _records(snapshot.data);
        return RefreshIndicator(
          onRefresh: () async => _reload(),
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
            children: [
              Text(
                widget.title,
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              if (widget.description != null) ...[
                const SizedBox(height: 6),
                Text(widget.description!),
              ],
              const SizedBox(height: 20),
              if (records.isEmpty)
                const SahajomySectionCard(
                  title: 'Nothing here yet',
                  children: [Text('No records are available yet.')],
                )
              else
                for (final record in records) ...[
                  _RecordCard(record: record),
                  const SizedBox(height: 10),
                ],
            ],
          ),
        );
      },
    ),
  );

  List<Map<String, dynamic>> _records(Object? value) {
    if (value is List) return value.whereType<Map>().map(_toStringMap).toList();
    if (value is! Map) return const [];
    final map = _toStringMap(value);
    for (final key in const [
      'items',
      'data',
      'results',
      'records',
      'batches',
      'orders',
      'containers',
      'reservations',
      'bookings',
      'notifications',
      'users',
      'categories',
      'operators',
      'requests',
      'logs',
      'shipments',
    ]) {
      final candidate = map[key];
      if (candidate is List) {
        return candidate.whereType<Map>().map(_toStringMap).toList();
      }
    }
    return [map];
  }

  Map<String, dynamic> _toStringMap(Map value) =>
      Map<String, dynamic>.from(value);
}

class _RecordCard extends StatelessWidget {
  const _RecordCard({required this.record});

  final Map<String, dynamic> record;

  @override
  Widget build(BuildContext context) {
    final title = _firstValue(record, const [
      'name',
      'title',
      'reference',
      'tracking_number',
      'order_number',
      'reservation_number',
      'email',
      'id',
    ]);
    final status = _firstValue(record, const ['status', 'state', 'stage']);
    final details = record.entries
        .where((entry) => entry.value != null && entry.key != 'id')
        .take(3)
        .map((entry) => '${_label(entry.key)}: ${entry.value}')
        .join('\n');
    return SahajomySectionCard(
      title: title,
      children: [
        Row(
          children: [
            const Spacer(),
            if (status.isNotEmpty) SahajomyStatusPill(label: status),
          ],
        ),
        if (details.isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(details, style: const TextStyle(fontSize: 12, height: 1.45)),
        ],
      ],
    );
  }

  String _firstValue(Map<String, dynamic> source, List<String> keys) {
    for (final key in keys) {
      final value = source[key];
      if (value != null && '$value'.isNotEmpty) return '$value';
    }
    return 'Sahajomy record';
  }

  String _label(String key) => key.replaceAll('_', ' ');
}
