import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../app/theme.dart';
import '../../../../core/utils/document_handler.dart';
import '../../../../features/repository_providers.dart';
import '../../../customer/presentation/customer_components.dart';

class CargoConsolidatedPackingListPage extends ConsumerStatefulWidget {
  const CargoConsolidatedPackingListPage({required this.containerId, super.key});
  final String containerId;

  @override
  ConsumerState<CargoConsolidatedPackingListPage> createState() => _CargoConsolidatedPackingListPageState();
}

class _CargoConsolidatedPackingListPageState extends ConsumerState<CargoConsolidatedPackingListPage> {
  late Future<Map<String, dynamic>> _packingList = _load();
  bool _busy = false;

  Future<Map<String, dynamic>> _load() => ref.read(cargoOperationsRepositoryProvider).getConsolidatedPackingList(widget.containerId);

  Future<void> _export({required bool share}) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final bytes = await ref.read(cargoOperationsRepositoryProvider).exportConsolidatedPackingListPdf(widget.containerId);
      final fileName = 'consolidated-packing-list-${widget.containerId}.pdf';
      if (share) {
        await DocumentHandler.saveAndShare(bytes: bytes, fileName: fileName);
      } else {
        await DocumentHandler.saveAndOpen(bytes: bytes, fileName: fileName);
      }
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Unable to ${share ? 'share' : 'open'} the packing list.')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'CONTAINER',
    title: 'Consolidated packing list',
    notificationRoute: '/cargo/notifications',
    body: FutureBuilder<Map<String, dynamic>>(
      future: _packingList,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
        if (snapshot.hasError) return CustomerEmptyState(icon: Icons.error_outline, message: 'The consolidated packing list is unavailable.', actionLabel: 'Retry', onAction: () => setState(() => _packingList = _load()));
        final payload = snapshot.data ?? const <String, dynamic>{};
        final summary = Map<String, dynamic>.from(payload['summary'] as Map? ?? const {});
        final items = (payload['items'] as List? ?? const []).whereType<Map>().toList();
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          children: [
            CustomerHeroCard(eyebrow: 'Packing list', title: 'Container consolidated list', subtitle: '${summary['sea_booking_count'] ?? 0} bookings · ${summary['total_cartons'] ?? 0} cartons · ${summary['total_cbm'] ?? 0} CBM'),
            const SizedBox(height: 20),
            if (items.isEmpty)
              const CustomerEmptyState(icon: Icons.inventory_2_outlined, message: 'No booking or packing-list items are available for this container.')
            else
              Container(
                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)),
                child: Column(children: [for (var index = 0; index < items.length; index++) ...[
                  ListTile(title: Text('${items[index]['item_name'] ?? 'Cargo item'}'), subtitle: Text('${items[index]['customer_name'] ?? 'Customer'} · ${items[index]['cbm'] ?? 0} CBM'), trailing: Text('${items[index]['cartons'] ?? 0} ctn')),
                  if (index < items.length - 1) const Divider(height: 1),
                ]]),
              ),
            const SizedBox(height: 24),
            Row(children: [
              Expanded(child: FilledButton.icon(onPressed: _busy ? null : () => _export(share: false), icon: const Icon(Icons.picture_as_pdf_outlined), label: Text(_busy ? 'Preparing…' : 'Open PDF'))),
              const SizedBox(width: 10),
              Expanded(child: OutlinedButton.icon(onPressed: _busy ? null : () => _export(share: true), icon: const Icon(Icons.share_outlined), label: const Text('Share'))),
            ]),
          ],
        );
      },
    ),
  );
}
