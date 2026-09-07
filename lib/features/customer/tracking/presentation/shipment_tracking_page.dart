import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../app/theme.dart';
import '../../../../core/ui/logistics_ui.dart';
import '../../../../core/ui/sahajomy_ui.dart';
import '../../presentation/customer_components.dart';
import '../../../repository_providers.dart';

class ShipmentTrackingPage extends ConsumerStatefulWidget {
  const ShipmentTrackingPage({this.entityId, super.key});
  final String? entityId;
  @override
  ConsumerState<ShipmentTrackingPage> createState() => _TrackingState();
}

class _TrackingState extends ConsumerState<ShipmentTrackingPage> {
  late Future<List<Map<String, dynamic>>> _events;
  String _search = '';
  @override
  void initState() {
    super.initState();
    _events = _load();
  }

  Future<List<Map<String, dynamic>>> _load() =>
      ref.read(customerTrackingRepositoryProvider).listEvents();
  Future<void> _reload() async {
    final next = _load();
    setState(() => _events = next);
    try {
      await next;
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Shipment tracking',
    body: FutureBuilder<List<Map<String, dynamic>>>(
      future: _events,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return SahajomyMessageState(
            icon: Icons.cloud_off_outlined,
            message: logisticsError(snapshot.error, 'shipment updates'),
            actionLabel: 'Reload tracking',
            onAction: _reload,
          );
        }
        final events = (snapshot.data ?? [])
            .where(
              (e) =>
                  (widget.entityId == null ||
                      '${e['entity_id']}' == widget.entityId) &&
                  '${e['description']} ${e['display_reference']} ${e['event_type']}'
                      .toLowerCase()
                      .contains(_search.toLowerCase()),
            )
            .toList();
        return RefreshIndicator(
          onRefresh: _reload,
          child: ListView.builder(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
            itemCount: events.length + 1,
            itemBuilder: (context, index) {
              if (index == 0) {
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const CustomerHeroCard(
                      eyebrow: 'Shipment visibility',
                      title: 'Follow your cargo',
                      subtitle: 'Latest warehouse and freight updates, as reported by your cargo provider.',
                    ),
                    const SizedBox(height: 20),
                    TextField(
                      onChanged: (value) => setState(() => _search = value),
                      decoration: const InputDecoration(
                        labelText: 'Search shipment updates',
                        prefixIcon: Icon(Icons.search),
                      ),
                    ),
                    const SizedBox(height: 24),
                    if (events.isEmpty)
                      const CustomerEmptyState(
                        icon: Icons.route_outlined,
                        message: 'No shipment updates match this view. Warehouse and shipping events will appear as they are recorded.',
                      ),
                  ],
                );
              }
              final event = events[index - 1];
              return IntrinsicHeight(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    SizedBox(
                      width: 26,
                      child: Column(
                        children: [
                          const Icon(
                            Icons.check_circle_outline_rounded,
                            color: brandTeal,
                            size: 22,
                          ),
                          if (index < events.length)
                            const Expanded(
                              child: VerticalDivider(
                                color: appBorder,
                                thickness: 2,
                              ),
                            ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Padding(
                        padding: const EdgeInsets.only(bottom: 28),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              sahajomyTitleCase(
                                '${event['stage_label'] ?? event['event_type'] ?? 'Shipment update'}',
                              ),
                              style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: appInk),
                            ),
                            if (event['display_reference'] != null)
                              Text(
                                '${event['display_reference']}',
                                style: const TextStyle(fontWeight: FontWeight.w700),
                              ),
                            if (event['description'] != null) ...[
                              const SizedBox(height: 6),
                              Text('${event['description']}'),
                            ],
                            const SizedBox(height: 8),
                            Text(
                              logisticsDate(event['timestamp']),
                              style: const TextStyle(fontSize: 12, color: appMuted),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
        );
      },
    ),
  );
}
