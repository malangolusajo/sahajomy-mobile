import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sahajomy_mobile/features/repository_providers.dart';

import '../../presentation/customer_components.dart';
import '../../documents/presentation/invoice_receipt_detail_page.dart';
import '../data/customer_booking_repository.dart';

class BookingDetailPage extends ConsumerStatefulWidget {
  const BookingDetailPage({super.key, required this.bookingId});

  final String bookingId;

  @override
  ConsumerState<BookingDetailPage> createState() => _BookingDetailPageState();
}

class _BookingDetailPageState extends ConsumerState<BookingDetailPage> {
  CustomerBookingRepository get _repository =>
      ref.read(customerBookingRepositoryProvider);
  late Future<Map<String, dynamic>> _booking = Future.microtask(() => _load());

  Future<Map<String, dynamic>> _load() =>
      _repository.getBooking(widget.bookingId);

  void _retry() => setState(() => _booking = _load());

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Booking details',
    body: FutureBuilder<Map<String, dynamic>>(
      future: _booking,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return CustomerEmptyState(
            icon: Icons.error_outline,
            message: 'We could not load this booking.',
            actionLabel: 'Try again',
            onAction: _retry,
          );
        }
        final booking = snapshot.data!;
        final invoices = (booking['invoices'] as List? ?? const [])
            .cast<Map<String, dynamic>>();
        final receipts = (booking['receipts'] as List? ?? const [])
            .cast<Map<String, dynamic>>();
        final packingLists = (booking['packing_lists'] as List? ?? const [])
            .cast<Map<String, dynamic>>();
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          children: [
            const CustomerHeroCard(
              eyebrow: 'Booking',
              title: 'Booking details',
              subtitle: 'Review route, CBM, payment, goods state, documents, and tracking.',
            ),
            const SizedBox(height: 24),
            _SectionCard(
              title: 'Shipment',
              children: [
                _DetailRow(
                  'Reference',
                  booking['sea_booking_id'] ?? booking['id'],
                ),
                _DetailRow('Cargo status', booking['goods_status']),
                _DetailRow('Booked space', '${booking['cbm_booked'] ?? 0} CBM'),
                _DetailRow('Tracking', booking['tracking_number']),
                _DetailRow('Latest update', booking['latest_update']),
              ],
            ),
            if (booking['shipping_label_available'] == true) ...[
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: () => context.push(
                  '/customer/shipping-mark?sea_booking_id=${widget.bookingId}',
                ),
                icon: const Icon(Icons.qr_code_2_rounded),
                label: const Text('View shipping label'),
              ),
            ],
            const SizedBox(height: 16),
            _SectionCard(
              title: 'Payment',
              children: [
                _DetailRow(
                  'Logistics charge',
                  '${booking['currency'] ?? 'TZS'} ${booking['logistics_charge'] ?? 0}',
                ),
                _DetailRow('Payment status', booking['payment_status']),
                _DetailRow('Goods status', booking['goods_status']),
              ],
            ),
            const SizedBox(height: 16),
            _DocumentSection(
              title: 'Invoices',
              documents: invoices,
              numberKey: 'invoice_number',
              seaBookingId: widget.bookingId,
              type: 'invoice',
            ),
            const SizedBox(height: 16),
            _DocumentSection(
              title: 'Receipts',
              documents: receipts,
              numberKey: 'receipt_number',
              seaBookingId: widget.bookingId,
              type: 'receipt',
            ),
            const SizedBox(height: 16),
            _DocumentSection(
              title: 'Packing lists',
              documents: packingLists,
              numberKey: 'id',
              seaBookingId: widget.bookingId,
              type: 'packing_list',
            ),
          ],
        );
      },
    ),
  );
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({required this.title, required this.children});

  final String title;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          ...children,
        ],
      ),
    ),
  );
}

class _DetailRow extends StatelessWidget {
  const _DetailRow(this.label, this.value);

  final String label;
  final Object? value;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 4),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(width: 120, child: Text(label)),
        Expanded(child: Text(value?.toString() ?? 'Not available')),
      ],
    ),
  );
}

class _DocumentSection extends StatelessWidget {
  const _DocumentSection({
    required this.title,
    required this.documents,
    required this.numberKey,
    required this.seaBookingId,
    required this.type,
  });

  final String title;
  final List<Map<String, dynamic>> documents;
  final String numberKey;
  final String seaBookingId;
  final String type;

  @override
  Widget build(BuildContext context) => _SectionCard(
    title: title,
    children: documents.isEmpty
        ? const [Text('No documents available yet.')]
        : documents
              .map(
                (document) => ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.description_outlined),
                  title: Text(document[numberKey]?.toString() ?? 'Document'),
                  subtitle: Text(document['status']?.toString() ?? 'Available'),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () {
                    final page = switch (type) {
                      'invoice' => InvoiceDetailPage(
                        invoice: document,
                        seaBookingId: seaBookingId,
                      ),
                      'receipt' => ReceiptDetailPage(
                        receipt: document,
                        seaBookingId: seaBookingId,
                      ),
                      _ => CustomerPackingListDetailPage(document: document),
                    };
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => page),
                    );
                  },
                ),
              )
              .toList(),
  );
}
