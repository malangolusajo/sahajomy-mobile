import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/ui/logistics_ui.dart';
import '../../../core/ui/sahajomy_ui.dart';
import '../../repository_providers.dart';

class RecordDetailPage extends ConsumerStatefulWidget {
  const RecordDetailPage({required this.title, required this.endpoint, super.key});
  final String title;
  final String endpoint;
  @override
  ConsumerState<RecordDetailPage> createState() => _RecordDetailState();
}

class _RecordDetailState extends ConsumerState<RecordDetailPage> {
  late Future<Object> _record;
  @override
  void initState() { super.initState(); _record = _load(); }
  Future<Object> _load() => ref.read(workflowApiRepositoryProvider).load(widget.endpoint);
  @override
  Widget build(BuildContext context) => FutureBuilder<Object>(future: _record, builder: (context, snapshot) {
    if (snapshot.connectionState == ConnectionState.done && snapshot.data is Map) {
      return LogisticsRecordDetail(record: Map<String, dynamic>.from(snapshot.data! as Map), title: widget.title);
    }
    return Scaffold(appBar: SahajomyScreenHeader(title: widget.title), body:
      snapshot.connectionState != ConnectionState.done ? const Center(child: CircularProgressIndicator()) : SahajomyMessageState(
        icon: Icons.cloud_off_outlined, message: logisticsError(snapshot.error, widget.title.toLowerCase()),
        actionLabel: 'Reload details', onAction: () => setState(() => _record = _load()),
      ),
    );
  });
}
