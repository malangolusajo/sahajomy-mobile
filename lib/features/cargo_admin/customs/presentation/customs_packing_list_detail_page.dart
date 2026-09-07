import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/utils/document_handler.dart';
import '../../../../features/repository_providers.dart';
import '../../../../core/ui/sahajomy_ui.dart';
import '../../../customer/presentation/customer_components.dart';

class CustomsPackingListDetailPage extends ConsumerStatefulWidget {
  const CustomsPackingListDetailPage({required this.packingListId, super.key});
  final String packingListId;

  @override
  ConsumerState<CustomsPackingListDetailPage> createState() =>
      _CustomsPackingListDetailPageState();
}

class _CustomsPackingListDetailPageState
    extends ConsumerState<CustomsPackingListDetailPage> {
  late Future<Map<String, dynamic>> _document = _load();
  bool _busy = false;

  Future<Map<String, dynamic>> _load() => ref
      .read(cargoAdminDocumentsRepositoryProvider)
      .getCustomsPackingList(widget.packingListId);

  Future<void> _export({required bool share}) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final bytes = await ref
          .read(cargoAdminDocumentsRepositoryProvider)
          .downloadCustomsPackingListPdf(widget.packingListId);
      final fileName = 'customs-packing-list-${widget.packingListId}.pdf';
      if (share) {
        await DocumentHandler.saveAndShare(bytes: bytes, fileName: fileName);
      } else {
        await DocumentHandler.saveAndOpen(bytes: bytes, fileName: fileName);
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Unable to ${share ? 'share' : 'open'} the packing list.',
            ),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _changeStatus({required bool finalize}) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final repository = ref.read(cargoAdminDocumentsRepositoryProvider);
      if (finalize) {
        await repository.finalizeCustomsPackingList(widget.packingListId);
      } else {
        await repository.cancelCustomsPackingList(widget.packingListId);
      }
      if (mounted) setState(() => _document = _load());
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Unable to ${finalize ? 'finalize' : 'cancel'} the packing list.',
            ),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(
      role: 'Cargo Admin',
      title: 'Packing list',
    ),
    body: FutureBuilder<Map<String, dynamic>>(
      future: _document,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return SahajomyMessageState(
            icon: Icons.error_outline,
            message: 'The packing list could not be loaded.',
            actionLabel: 'Retry',
            onAction: () => setState(() => _document = _load()),
          );
        }
        final document = snapshot.data ?? const <String, dynamic>{};
        final items = (document['items'] as List? ?? const [])
            .whereType<Map>()
            .toList();
        final status = '${document['status'] ?? 'draft'}';
        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            CustomerHeroCard(
              eyebrow: 'Customs packing list',
              title:
                  '${document['packing_list_number'] ?? document['reference'] ?? 'Packing list'}',
              subtitle:
                  '${document['customer_name'] ?? document['consignee_name'] ?? 'Customer'} · ${status.replaceAll('_', ' ')}',
            ),
            const SizedBox(height: 16),
            SahajomyKeyValueList(
              entries: {
                'Cargo type': document['cargo_type'],
                'Cartons': document['total_cartons'],
                'Quantity': document['total_quantity'],
                'Gross weight': document['total_gross_weight_kg'],
                'CBM': document['total_cbm'],
                'Origin': document['origin_address'],
                'Notes': document['notes'],
              },
            ),
            const SizedBox(height: 20),
            Text('Items', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            if (items.isEmpty)
              const Text('No line items are recorded.')
            else
              for (final raw in items)
                Card(
                  child: ListTile(
                    title: Text(
                      '${raw['description'] ?? raw['item_name'] ?? 'Cargo item'}',
                    ),
                    subtitle: Text(
                      '${raw['cartons'] ?? 0} cartons · ${raw['cbm'] ?? 0} CBM · ${raw['gross_weight_kg'] ?? raw['weight_kg'] ?? 0} kg',
                    ),
                  ),
                ),
            const SizedBox(height: 20),
            Row(
              children: [
                Expanded(
                  child: FilledButton.icon(
                    onPressed: _busy ? null : () => _export(share: false),
                    icon: const Icon(Icons.picture_as_pdf_outlined),
                    label: const Text('Open PDF'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _busy ? null : () => _export(share: true),
                    icon: const Icon(Icons.share_outlined),
                    label: const Text('Share'),
                  ),
                ),
              ],
            ),
            if (status == 'draft') ...[
              const SizedBox(height: 12),
              FilledButton(
                onPressed: _busy ? null : () => _changeStatus(finalize: true),
                child: const Text('Finalize packing list'),
              ),
              TextButton(
                onPressed: _busy ? null : () => _changeStatus(finalize: false),
                child: const Text('Cancel packing list'),
              ),
            ],
          ],
        );
      },
    ),
  );
}
