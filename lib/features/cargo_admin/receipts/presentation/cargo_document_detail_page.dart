import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../app/theme.dart';
import '../../../../core/utils/document_handler.dart';
import '../../../../features/repository_providers.dart';
import '../../../customer/presentation/customer_components.dart';

class CargoDocumentDetailPage extends ConsumerStatefulWidget {
  const CargoDocumentDetailPage({
    required this.documentId,
    required this.type,
    super.key,
  });
  final String documentId;
  final String type;

  @override
  ConsumerState<CargoDocumentDetailPage> createState() =>
      _CargoDocumentDetailPageState();
}

class _CargoDocumentDetailPageState
    extends ConsumerState<CargoDocumentDetailPage> {
  late Future<Map<String, dynamic>> _document = _load();
  bool _busy = false;
  String? _generatedInvoiceId;

  Future<Map<String, dynamic>> _load() async {
    final repository = ref.read(cargoOperationsRepositoryProvider);
    final list = widget.type == 'receipt'
        ? await repository.listReceipts()
        : await repository.listInvoices();
    return list.firstWhere(
      (row) =>
          '${row[widget.type == 'receipt' ? 'receipt_id' : 'sea_booking_id'] ?? row['id']}' ==
          widget.documentId,
      orElse: () => <String, dynamic>{},
    );
  }

  String _seaBookingId(Map<String, dynamic> document) =>
      '${document['sea_booking_id'] ?? ''}';
  String _documentId(Map<String, dynamic> document) => widget.type == 'receipt'
      ? '${document['receipt_id'] ?? document['id'] ?? ''}'
      : _generatedInvoiceId ?? '${document['id'] ?? ''}';

  Future<String?> _ensureInvoice(Map<String, dynamic> document) async {
    if (widget.type != 'invoice') return _documentId(document);
    if (_generatedInvoiceId != null) return _generatedInvoiceId;
    final result = await ref
        .read(cargoOperationsRepositoryProvider)
        .generateInvoice(
          _seaBookingId(document),
          format: 'pdf',
          sendToCustomer: false,
        );
    _generatedInvoiceId = '${result['invoice_id'] ?? ''}';
    return _generatedInvoiceId;
  }

  Future<Uint8List> _download(Map<String, dynamic> document) async {
    final repository = ref.read(cargoOperationsRepositoryProvider);
    final id = await _ensureInvoice(document);
    if (id == null || id.isEmpty || _seaBookingId(document).isEmpty) {
      throw const FormatException('Document identifiers are missing.');
    }
    return widget.type == 'receipt'
        ? repository.downloadReceiptPdf(
            seaBookingId: _seaBookingId(document),
            receiptId: id,
          )
        : repository.downloadInvoicePdf(
            seaBookingId: _seaBookingId(document),
            invoiceId: id,
          );
  }

  Future<void> _run(
    Map<String, dynamic> document, {
    required bool share,
  }) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final bytes = await _download(document);
      final number =
          '${document['receipt_number'] ?? document['invoice_reference'] ?? widget.type}';
      if (share) {
        await DocumentHandler.saveAndShare(
          bytes: bytes,
          fileName: '$number.pdf',
          subject: number,
        );
      } else {
        await DocumentHandler.saveAndOpen(
          bytes: bytes,
          fileName: '$number.pdf',
        );
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
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: widget.type.toUpperCase(),
    title: widget.type == 'receipt' ? 'Receipt' : 'Invoice',
    notificationRoute: '/cargo/notifications',
    body: FutureBuilder<Map<String, dynamic>>(
      future: _document,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError || (snapshot.data?.isEmpty ?? true)) {
          return CustomerEmptyState(
            icon: Icons.error_outline,
            message: 'This document could not be loaded.',
            actionLabel: 'Retry',
            onAction: () => setState(() => _document = _load()),
          );
        }
        final d = snapshot.data!;
        final reference =
            '${d['receipt_number'] ?? d['invoice_reference'] ?? 'Document'}';
        final amount = d['total_amount'] ?? d['amount'] ?? 0;
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          children: [
            CustomerHeroCard(
              eyebrow: widget.type,
              title: reference,
              subtitle:
                  '${d['customer_name'] ?? 'Customer'} · ${d['currency'] ?? ''} $amount',
            ),
            const SizedBox(height: 20),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: appBorder),
              ),
              child: Column(
                children: [
                  _kv('Amount', '${d['currency'] ?? ''} $amount'),
                  const Divider(),
                  _kv(
                    'Status',
                    '${d['status'] ?? 'issued'}'.replaceAll('_', ' '),
                  ),
                  const Divider(),
                  _kv(
                    'Booking',
                    _seaBookingId(d).isEmpty
                        ? 'Not available'
                        : _seaBookingId(d),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: FilledButton.icon(
                    onPressed: _busy ? null : () => _run(d, share: false),
                    icon: const Icon(Icons.picture_as_pdf_outlined),
                    label: Text(
                      _busy
                          ? 'Preparing…'
                          : widget.type == 'invoice'
                          ? 'Generate PDF'
                          : 'Open PDF',
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _busy ? null : () => _run(d, share: true),
                    icon: const Icon(Icons.share_outlined),
                    label: const Text('Share PDF'),
                  ),
                ),
              ],
            ),
          ],
        );
      },
    ),
  );

  Widget _kv(String label, String value) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 8),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(color: appMuted, fontSize: 14)),
        const SizedBox(width: 16),
        Expanded(
          child: Text(
            value,
            textAlign: TextAlign.right,
            style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
          ),
        ),
      ],
    ),
  );
}
