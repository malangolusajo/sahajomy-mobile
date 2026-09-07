import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/ui/logistics_ui.dart';
import '../../../core/ui/sahajomy_ui.dart';
import '../../repository_providers.dart';

/// Reusable record browser. No fabricated metrics or arbitrary JSON fields.
class LiveWorkflowPage extends ConsumerStatefulWidget {
  const LiveWorkflowPage({required this.role, required this.title, required this.endpoint,
    this.description, this.actionLabel, this.actionRoute, this.embedded = false, super.key});
  final String role;
  final String title;
  final String endpoint;
  final String? description;
  final String? actionLabel;
  final String? actionRoute;
  final bool embedded;
  @override
  ConsumerState<LiveWorkflowPage> createState() => _LiveWorkflowPageState();
}

class _LiveWorkflowPageState extends ConsumerState<LiveWorkflowPage> {
  late Future<Object> _result;
  String _query = '';
  @override
  void initState() { super.initState(); _result = _load(); }
  Future<Object> _load() => ref.read(workflowApiRepositoryProvider).load(widget.endpoint);
  Future<void> _reload() async {
    final result = _load();
    setState(() => _result = result);
    try { await result; } catch (_) { /* Render the contextual error state. */ }
  }
  @override
  Widget build(BuildContext context) {
    final body = FutureBuilder<Object>(future: _result, builder: (context, snapshot) {
      if (snapshot.connectionState != ConnectionState.done) {
        return Center(child: Semantics(label: 'Loading ${widget.title.toLowerCase()}', child: const CircularProgressIndicator()));
      }
      if (snapshot.hasError) return SahajomyMessageState(
        icon: Icons.cloud_off_outlined, message: logisticsError(snapshot.error, widget.title.toLowerCase()),
        actionLabel: 'Reload ${widget.title.toLowerCase()}', onAction: _reload,
      );
      final records = workflowRecords(snapshot.data);
      final filtered = records.where((r) => logisticsDetails(r).values.join(' ').toLowerCase().contains(_query.toLowerCase())).toList();
      return RefreshIndicator(onRefresh: _reload, child: CustomScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        slivers: [
          SliverPadding(padding: const EdgeInsets.fromLTRB(24, 20, 24, 0), sliver: SliverToBoxAdapter(child: Column(children: [
            LogisticsIntro(title: widget.title, description: widget.description ?? 'Review ${widget.title.toLowerCase()} in your ${widget.role == 'Public' ? 'Sahajomy' : widget.role.toLowerCase()} workspace.'),
            if (widget.actionRoute != null && widget.actionLabel != null) ...[
              SizedBox(width: double.infinity, child: FilledButton.icon(onPressed: () => context.push(widget.actionRoute!), icon: const Icon(Icons.add_rounded), label: Text(widget.actionLabel!))),
              const SizedBox(height: 20),
            ],
            TextField(onChanged: (value) => setState(() => _query = value), decoration: InputDecoration(prefixIcon: const Icon(Icons.search_rounded), labelText: 'Search ${widget.title.toLowerCase()}')),
            const SizedBox(height: 20),
          ]))),
          if (filtered.isEmpty) SliverFillRemaining(hasScrollBody: false, child: SahajomyMessageState(
            icon: Icons.inventory_2_outlined,
            message: _query.isEmpty ? 'No ${widget.title.toLowerCase()} available yet.' : 'No ${widget.title.toLowerCase()} match your search.',
          )) else SliverPadding(padding: const EdgeInsets.fromLTRB(24, 0, 24, 32), sliver: SliverList.separated(
            itemCount: filtered.length,
            separatorBuilder: (_, _) => const Divider(height: 1),
            itemBuilder: (_, index) => LogisticsRecordTile(record: filtered[index], subject: widget.title),
          )),
        ],
      ));
    });
    return widget.embedded ? Material(color: Theme.of(context).scaffoldBackgroundColor, child: body) : Scaffold(appBar: SahajomyScreenHeader(role: widget.role, title: widget.title), body: body);
  }
}

List<Map<String, dynamic>> workflowRecords(Object? value) {
  if (value is List) return value.whereType<Map>().map((v) => Map<String, dynamic>.from(v)).toList();
  if (value is! Map || value.isEmpty) return const [];
  for (final key in const ['items', 'data', 'results', 'records', 'products', 'agents', 'batches', 'orders', 'containers', 'sea_bookings', 'bookings', 'notifications', 'users', 'categories', 'operators', 'requests', 'logs', 'shipments', 'addresses', 'companies', 'services', 'invoices', 'receipts', 'packing_lists']) {
    if (value[key] is List) return workflowRecords(value[key]);
  }
  return [Map<String, dynamic>.from(value)];
}
