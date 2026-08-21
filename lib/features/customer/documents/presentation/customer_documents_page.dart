import 'package:flutter/material.dart';

import '../../../../core/ui/sahajomy_ui.dart';
import '../../reservations/data/customer_reservations_repository.dart';
import '../../reservations/presentation/reservation_detail_page.dart';

class CustomerDocumentsPage extends StatefulWidget {
  const CustomerDocumentsPage({super.key});

  @override
  State<CustomerDocumentsPage> createState() => _CustomerDocumentsPageState();
}

class _CustomerDocumentsPageState extends State<CustomerDocumentsPage> {
  final _repository = CustomerReservationsRepository();
  late Future<List<_CustomerDocument>> _documents = _loadDocuments();

  Future<List<_CustomerDocument>> _loadDocuments() async {
    final reservations = await _repository.listReservations();
    final details = await Future.wait(
      reservations.map(
        (reservation) => _repository.getReservation('${reservation['id']}'),
      ),
    );
    return [
      for (final reservation in details)
        for (final entry in <String, String>{
          'invoices': 'Commercial invoice',
          'receipts': 'Payment receipt',
          'packing_lists': 'Packing list',
        }.entries)
          for (final document in (reservation[entry.key] as List? ?? const []))
            _CustomerDocument(
              reservationId: '${reservation['id']}',
              title:
                  '${(document as Map)['name'] ?? (document)['title'] ?? entry.value}',
              subtitle: '${entry.value} · ${document['status'] ?? 'Available'}',
            ),
    ];
  }

  void _retry() => setState(() => _documents = _loadDocuments());

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(role: 'Customer', title: 'Documents'),
    body: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Padding(
          padding: EdgeInsets.fromLTRB(20, 20, 20, 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Shipping documents',
                style: TextStyle(fontSize: 26, fontWeight: FontWeight.w800),
              ),
              SizedBox(height: 4),
              Text(
                'Invoices, receipts, and shipping files available for download.',
              ),
            ],
          ),
        ),
        Expanded(
          child: FutureBuilder<List<_CustomerDocument>>(
            future: _documents,
            builder: (context, snapshot) {
              if (snapshot.connectionState != ConnectionState.done) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snapshot.hasError) {
                return SahajomyMessageState(
                  icon: Icons.error_outline,
                  message: 'We could not load your shipping documents.',
                  actionLabel: 'Try again',
                  onAction: _retry,
                );
              }
              final documents = snapshot.data!;
              if (documents.isEmpty) {
                return const SahajomyMessageState(
                  icon: Icons.description_outlined,
                  message: 'No shipping documents are available yet.',
                );
              }
              return ListView.separated(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
                itemCount: documents.length,
                separatorBuilder: (_, _) => const SizedBox(height: 12),
                itemBuilder: (context, index) =>
                    _DocumentCard(document: documents[index]),
              );
            },
          ),
        ),
      ],
    ),
  );
}

class _CustomerDocument {
  const _CustomerDocument({
    required this.reservationId,
    required this.title,
    required this.subtitle,
  });

  final String reservationId;
  final String title;
  final String subtitle;
}

class _DocumentCard extends StatelessWidget {
  const _DocumentCard({required this.document});

  final _CustomerDocument document;

  @override
  Widget build(BuildContext context) => Card(
    child: ListTile(
      contentPadding: const EdgeInsets.all(16),
      leading: const Icon(Icons.picture_as_pdf_outlined),
      title: Text(
        document.title,
        style: const TextStyle(fontWeight: FontWeight.w800),
      ),
      subtitle: Text(document.subtitle),
      trailing: const SahajomyStatusPill(label: 'PDF'),
      onTap: () => Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) =>
              ReservationDetailPage(reservationId: document.reservationId),
        ),
      ),
    ),
  );
}
