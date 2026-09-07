import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../../../features/repository_providers.dart';
import '../../../customer/presentation/customer_components.dart';

class CargoDocumentDetailPage extends ConsumerStatefulWidget {
  const CargoDocumentDetailPage({required this.documentId, required this.type, super.key});
  final String documentId;
  final String type; // 'receipt' or 'invoice'

  @override
  ConsumerState<CargoDocumentDetailPage> createState() => _CargoDocumentDetailPageState();
}

class _CargoDocumentDetailPageState extends ConsumerState<CargoDocumentDetailPage> {
  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: widget.type.toUpperCase(),
    title: widget.type == 'receipt' ? 'Receipt' : 'Invoice',
    notificationRoute: '/cargo/notifications',
    body: FutureBuilder<Map<String, dynamic>>(
      future: widget.type == 'receipt'
          ? ref.read(cargoOperationsRepositoryProvider).listReceipts().then((l) => l.firstWhere((e) => e['id'] == widget.documentId, orElse: () => {}))
          : ref.read(cargoOperationsRepositoryProvider).listInvoices().then((l) => l.firstWhere((e) => e['id'] == widget.documentId, orElse: () => {})),
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
        final d = snapshot.data ?? {};
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          children: [
            CustomerHeroCard(eyebrow: widget.type, title: d['reference'] ?? 'Document', subtitle: '${d['customer_name'] ?? 'Customer'} · ${d['amount'] ?? 0} ${d['currency'] ?? 'TZS'}'),
            const SizedBox(height: 20),
            Container(padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)), child: Column(children: [
              _kv('Amount', '${d['amount'] ?? 0} ${d['currency'] ?? 'TZS'}'),
              const Divider(),
              _kv('Status', (d['status'] ?? 'paid').toString().replaceAll('_', ' ')),
              const Divider(),
              _kv('Booking', d['reservation_reference'] ?? '—'),
            ])),
            const SizedBox(height: 24),
            Row(children: [
              Expanded(child: FilledButton.icon(onPressed: () {}, icon: const Icon(Icons.picture_as_pdf), label: const Text('Download PDF'))),
              const SizedBox(width: 10),
              Expanded(child: OutlinedButton.icon(onPressed: () {}, icon: const Icon(Icons.share), label: const Text('Share'))),
            ]),
          ],
        );
      },
    ),
  );

  Widget _kv(String label, String value) => Padding(padding: const EdgeInsets.symmetric(vertical: 8), child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
    Text(label, style: const TextStyle(color: appMuted, fontSize: 14)),
    Text(value, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
  ]));
}
