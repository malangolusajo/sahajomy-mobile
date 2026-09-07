import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sahajomy_mobile/features/repository_providers.dart';

import '../../../../core/ui/sahajomy_ui.dart';
import '../../presentation/customer_components.dart';
import '../../reservations/data/customer_booking_repository.dart';
import '../../reservations/presentation/booking_detail_page.dart';

class CustomerDocumentsPage extends ConsumerStatefulWidget {
  const CustomerDocumentsPage({super.key});

  @override
  ConsumerState<CustomerDocumentsPage> createState() =>
      _CustomerDocumentsPageState();
}

class _CustomerDocumentsPageState extends ConsumerState<CustomerDocumentsPage> {
  CustomerBookingRepository get _repository =>
      ref.read(customerBookingRepositoryProvider);
  late Future<List<_CustomerDocument>> _documents = Future.microtask(
    () => _loadDocuments(),
  );

  Future<List<_CustomerDocument>> _loadDocuments() async {
    final bookings = await _repository.listBookings();
    final details = await Future.wait(
      bookings.map(
        (booking) => _repository.getBooking('${booking['sea_booking_id'] ?? booking['id']}'),
      ),
    );
    return [
      for (final booking in details)
        for (final entry in <String, String>{
          'invoices': 'Commercial invoice',
          'receipts': 'Payment receipt',
          'packing_lists': 'Packing list',
        }.entries)
          for (final document in (booking[entry.key] as List? ?? const []))
            _CustomerDocument(
              bookingId: '${booking['sea_booking_id'] ?? booking['id']}',
              title:
                  '${(document as Map)['name'] ?? (document)['title'] ?? entry.value}',
              subtitle: '${entry.value} · ${document['status'] ?? 'Available'}',
            ),
    ];
  }

  void _retry() => setState(() => _documents = _loadDocuments());

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Documents',
    body: FutureBuilder<List<_CustomerDocument>>(
      future: _documents,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return CustomerEmptyState(
            icon: Icons.error_outline,
            message: 'We could not load your shipping documents.',
            actionLabel: 'Try again',
            onAction: _retry,
          );
        }
        final documents = snapshot.data!;
        if (documents.isEmpty) {
          return const CustomerEmptyState(
            icon: Icons.description_outlined,
            message: 'No shipping documents are available yet.',
          );
        }
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          children: [
            const CustomerHeroCard(
              eyebrow: 'Financial documents',
              title: 'Documents',
              subtitle: 'Documents use the booking or order currency captured by the backend.',
            ),
            const SizedBox(height: 24),
            for (final document in documents) ...[
              _DocumentCard(document: document),
              const SizedBox(height: 12),
            ],
          ],
        );
      },
    ),
  );
}

class _CustomerDocument {
  const _CustomerDocument({
    required this.bookingId,
    required this.title,
    required this.subtitle,
  });

  final String bookingId;
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
              BookingDetailPage(bookingId: document.bookingId),
        ),
      ),
    ),
  );
}
