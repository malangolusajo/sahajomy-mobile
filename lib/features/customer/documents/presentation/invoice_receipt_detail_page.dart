import 'package:flutter/material.dart';

import '../../../../app/theme.dart';
import '../../presentation/customer_components.dart';

class InvoiceDetailPage extends StatelessWidget {
  const InvoiceDetailPage({required this.invoice, this.reservationId, super.key});

  final Map<String, dynamic> invoice;
  final String? reservationId;

  @override
  Widget build(BuildContext context) => _DocumentDetailPage(
    title: 'Invoice',
    document: invoice,
    reservationId: reservationId,
    type: 'invoice',
  );
}

class ReceiptDetailPage extends StatelessWidget {
  const ReceiptDetailPage({required this.receipt, this.reservationId, super.key});

  final Map<String, dynamic> receipt;
  final String? reservationId;

  @override
  Widget build(BuildContext context) => _DocumentDetailPage(
    title: 'Receipt',
    document: receipt,
    reservationId: reservationId,
    type: 'receipt',
  );
}

class _DocumentDetailPage extends StatelessWidget {
  const _DocumentDetailPage({
    required this.title,
    required this.document,
    required this.reservationId,
    required this.type,
  });

  final String title;
  final Map<String, dynamic> document;
  final String? reservationId;
  final String type;

  @override
  Widget build(BuildContext context) {
    final number = document['${type}_number'] ?? document['invoice_number'] ?? '—';
    final currency = document['currency'] ?? '—';
    final amount = document['amount'] ?? document['logistics_charge'] ?? 0;
    final status = document['status'] ?? 'open';
    final date = document['sent_at'] ?? document['generated_at'] ?? document['created_at'] ?? '—';
    return CustomerScaffold(
      title: title,
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          const CustomerHeroCard(
            eyebrow: 'Financial documents',
            title: 'Document',
            subtitle: 'Documents use the booking or order currency captured by the backend.',
          ),
          const SizedBox(height: 24),
          Container(
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: appBorder),
            ),
            child: Column(
              children: [
                _docRow('PDF', number, '$currency · ${date.toString().substring(0, 10)}', brandCoral, status),
                const Divider(height: 1, indent: 60),
                _docRow('XLS', 'Packing list', 'Line items · CBM', appMuted, 'Export'),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: appBorder),
            ),
            child: Column(
              children: [
                const Row(
                  children: [
                    Expanded(child: Text('Description', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 12, color: appMuted))),
                    SizedBox(width: 8),
                    SizedBox(width: 50, child: Text('Qty', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 12, color: appMuted))),
                    SizedBox(width: 8),
                    SizedBox(width: 80, child: Text('Amount', textAlign: TextAlign.right, style: TextStyle(fontWeight: FontWeight.w700, fontSize: 12, color: appMuted))),
                  ],
                ),
                const Divider(),
                const SizedBox(height: 8),
                _tableRow('Sea cargo', '4.8', '$currency $amount'),
                const SizedBox(height: 6),
                _tableRow('Handling', '1', '$currency 40'),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _docRow(String badge, String title, String subtitle, Color badgeColor, String tag) => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    child: Row(
      children: [
        Container(
          width: 40,
          height: 40,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: badgeColor.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Text(badge, style: TextStyle(color: badgeColor, fontWeight: FontWeight.w800)),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
              const SizedBox(height: 2),
              Text(subtitle, style: const TextStyle(color: appMuted, fontSize: 13)),
            ],
          ),
        ),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            color: brandNavy.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(20),
          ),
          child: Text(tag, style: const TextStyle(color: brandNavy, fontSize: 12, fontWeight: FontWeight.w700)),
        ),
      ],
    ),
  );

  Widget _tableRow(String desc, String qty, String amount) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 4),
    child: Row(
      children: [
        Expanded(child: Text(desc, style: const TextStyle(fontSize: 14))),
        SizedBox(width: 50, child: Text(qty, style: const TextStyle(fontSize: 14))),
        SizedBox(width: 80, child: Text(amount, textAlign: TextAlign.right, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600))),
      ],
    ),
  );
}
