import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../app/theme.dart';
import '../../../../core/utils/document_handler.dart';
import '../../../../features/repository_providers.dart';
import '../../presentation/customer_components.dart';

class InvoiceDetailPage extends StatelessWidget {
  const InvoiceDetailPage({
    required this.invoice,
    this.seaBookingId,
    super.key,
  });
  final Map<String, dynamic> invoice;
  final String? seaBookingId;

  @override
  Widget build(BuildContext context) => CustomerFinancialDocumentPage(
    title: 'Invoice',
    document: invoice,
    seaBookingId: seaBookingId,
    type: 'invoice',
  );
}

class ReceiptDetailPage extends StatelessWidget {
  const ReceiptDetailPage({
    required this.receipt,
    this.seaBookingId,
    super.key,
  });
  final Map<String, dynamic> receipt;
  final String? seaBookingId;

  @override
  Widget build(BuildContext context) => CustomerFinancialDocumentPage(
    title: 'Receipt',
    document: receipt,
    seaBookingId: seaBookingId,
    type: 'receipt',
  );
}

class CustomerPackingListDetailPage extends StatelessWidget {
  const CustomerPackingListDetailPage({required this.document, super.key});
  final Map<String, dynamic> document;

  @override
  Widget build(BuildContext context) {
    final items = (document['items'] as List? ?? const [])
        .whereType<Map>()
        .map(Map<String, dynamic>.from)
        .toList();
    return CustomerScaffold(
      title: 'Packing list',
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          CustomerHeroCard(
            eyebrow: 'Shipping document',
            title: 'Packing list',
            subtitle: 'Status: ${_label(document['status'])}',
          ),
          const SizedBox(height: 18),
          _FieldsCard(
            fields: {
              'Shipment stage': document['shipment_stage'],
              'Cartons': document['total_cartons'],
              'CBM': document['total_cbm'],
              'Weight (kg)': document['total_weight_kg'],
              'Received CBM': document['received_cbm'],
              'Loaded CBM': document['loaded_cbm'],
              'Updated': _date(document['updated_at']),
              'Notes': document['notes'],
            },
          ),
          const SizedBox(height: 18),
          Text('Items', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          if (items.isEmpty)
            const Text('No line items are available.')
          else
            for (final item in items)
              Card(
                child: ListTile(
                  title: Text(_label(item['item_name'])),
                  subtitle: Text(
                    '${item['cartons'] ?? 0} cartons · ${item['cbm'] ?? 0} CBM · ${item['weight_kg'] ?? 0} kg',
                  ),
                  trailing: Text(_label(item['status'])),
                ),
              ),
        ],
      ),
    );
  }
}

class CustomerFinancialDocumentPage extends ConsumerStatefulWidget {
  const CustomerFinancialDocumentPage({
    required this.title,
    required this.document,
    required this.seaBookingId,
    required this.type,
    super.key,
  });
  final String title;
  final Map<String, dynamic> document;
  final String? seaBookingId;
  final String type;

  @override
  ConsumerState<CustomerFinancialDocumentPage> createState() =>
      _CustomerFinancialDocumentPageState();
}

class _CustomerFinancialDocumentPageState
    extends ConsumerState<CustomerFinancialDocumentPage> {
  bool _busy = false;
  String get _id => '${widget.document['id'] ?? ''}';
  String get _number => _label(
    widget.document['${widget.type}_number'] ??
        widget.document['invoice_number'],
  );
  bool get _canDownload =>
      widget.seaBookingId?.isNotEmpty == true && _id.isNotEmpty;
  String get _fileName =>
      '${_number == 'Not available' ? widget.type : _number}.pdf';

  Future<Uint8List> _download() {
    final repository = ref.read(customerBookingRepositoryProvider);
    return widget.type == 'invoice'
        ? repository.downloadInvoicePdf(
            seaBookingId: widget.seaBookingId!,
            invoiceId: _id,
          )
        : repository.downloadReceiptPdf(
            seaBookingId: widget.seaBookingId!,
            receiptId: _id,
          );
  }

  Future<void> _run({required bool share}) async {
    if (!_canDownload || _busy) return;
    setState(() => _busy = true);
    try {
      final bytes = await _download();
      if (share) {
        await DocumentHandler.saveAndShare(
          bytes: bytes,
          fileName: _fileName,
          subject: '${widget.title} $_number',
        );
      } else {
        await DocumentHandler.saveAndOpen(bytes: bytes, fileName: _fileName);
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Unable to ${share ? 'share' : 'open'} this document.',
            ),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final document = widget.document;
    final amount = document['amount'] ?? document['total_amount'];
    return CustomerScaffold(
      title: widget.title,
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          CustomerHeroCard(
            eyebrow: 'Financial document',
            title: _number,
            subtitle: 'This document and its totals are generated by Sahajomy services.',
          ),
          const SizedBox(height: 18),
          _FieldsCard(
            fields: {
              'Amount': amount == null
                  ? null
                  : '${document['currency'] ?? ''} $amount'.trim(),
              'Status': document['status'],
              'Created': _date(
                document['sent_at'] ??
                    document['generated_at'] ??
                    document['created_at'],
              ),
              'Paid': _date(document['paid_at']),
              'Notes': document['notes'],
            },
          ),
          const SizedBox(height: 20),
          if (_canDownload)
            Row(
              children: [
                Expanded(
                  child: FilledButton.icon(
                    onPressed: _busy ? null : () => _run(share: false),
                    icon: const Icon(Icons.picture_as_pdf_outlined),
                    label: Text(_busy ? 'Opening…' : 'Open PDF'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _busy ? null : () => _run(share: true),
                    icon: const Icon(Icons.share_outlined),
                    label: const Text('Share'),
                  ),
                ),
              ],
            )
          else
            const Text(
              'The PDF is not available for this document yet.',
              style: TextStyle(color: appMuted),
            ),
        ],
      ),
    );
  }
}

class _FieldsCard extends StatelessWidget {
  const _FieldsCard({required this.fields});
  final Map<String, Object?> fields;

  @override
  Widget build(BuildContext context) {
    final visible = fields.entries
        .where(
          (entry) => entry.value != null && '${entry.value}'.trim().isNotEmpty,
        )
        .toList();
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: appBorder),
      ),
      child: Column(
        children: [
          for (var index = 0; index < visible.length; index++) ...[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SizedBox(
                  width: 112,
                  child: Text(
                    visible[index].key,
                    style: const TextStyle(color: appMuted),
                  ),
                ),
                Expanded(
                  child: Text(
                    _label(visible[index].value),
                    textAlign: TextAlign.right,
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                ),
              ],
            ),
            if (index < visible.length - 1) const Divider(height: 24),
          ],
        ],
      ),
    );
  }
}

String _label(Object? value) {
  final text = value?.toString().trim() ?? '';
  return text.isEmpty ? 'Not available' : text.replaceAll('_', ' ');
}

String? _date(Object? value) {
  final text = value?.toString().trim() ?? '';
  if (text.isEmpty) return null;
  final parsed = DateTime.tryParse(text);
  if (parsed == null) return text;
  return '${parsed.year.toString().padLeft(4, '0')}-${parsed.month.toString().padLeft(2, '0')}-${parsed.day.toString().padLeft(2, '0')}';
}
