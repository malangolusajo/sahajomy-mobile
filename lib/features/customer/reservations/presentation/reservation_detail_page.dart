import 'package:flutter/material.dart';

import '../data/customer_reservations_repository.dart';

class ReservationDetailPage extends StatefulWidget {
  const ReservationDetailPage({super.key, required this.reservationId});

  final String reservationId;

  @override
  State<ReservationDetailPage> createState() => _ReservationDetailPageState();
}

class _ReservationDetailPageState extends State<ReservationDetailPage> {
  final _repository = CustomerReservationsRepository();
  late Future<Map<String, dynamic>> _reservation = _load();

  Future<Map<String, dynamic>> _load() =>
      _repository.getReservation(widget.reservationId);

  void _retry() => setState(() => _reservation = _load());

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Reservation details')),
    body: FutureBuilder<Map<String, dynamic>>(
      future: _reservation,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return Center(
            child: OutlinedButton(
              onPressed: _retry,
              child: const Text('Try again'),
            ),
          );
        }
        final reservation = snapshot.data!;
        final invoices = (reservation['invoices'] as List? ?? const [])
            .cast<Map<String, dynamic>>();
        final receipts = (reservation['receipts'] as List? ?? const [])
            .cast<Map<String, dynamic>>();
        final packingLists = (reservation['packing_lists'] as List? ?? const [])
            .cast<Map<String, dynamic>>();
        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            _SectionCard(
              title: 'Shipment',
              children: [
                _DetailRow(
                  'Reference',
                  reservation['reservation_id'] ?? reservation['id'],
                ),
                _DetailRow('Status', reservation['status']),
                _DetailRow(
                  'Reserved space',
                  '${reservation['cbm_reserved'] ?? 0} CBM',
                ),
                _DetailRow('Tracking', reservation['tracking_number']),
                _DetailRow('Latest update', reservation['latest_update']),
              ],
            ),
            const SizedBox(height: 16),
            _SectionCard(
              title: 'Payment',
              children: [
                _DetailRow(
                  'Logistics charge',
                  '${reservation['currency'] ?? 'TZS'} ${reservation['logistics_charge'] ?? 0}',
                ),
                _DetailRow('Payment status', reservation['payment_status']),
                _DetailRow('Goods status', reservation['goods_status']),
              ],
            ),
            const SizedBox(height: 16),
            _DocumentSection(
              title: 'Invoices',
              documents: invoices,
              numberKey: 'invoice_number',
            ),
            const SizedBox(height: 16),
            _DocumentSection(
              title: 'Receipts',
              documents: receipts,
              numberKey: 'receipt_number',
            ),
            const SizedBox(height: 16),
            _DocumentSection(
              title: 'Packing lists',
              documents: packingLists,
              numberKey: 'id',
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
  });

  final String title;
  final List<Map<String, dynamic>> documents;
  final String numberKey;

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
                ),
              )
              .toList(),
  );
}
