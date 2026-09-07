import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../../../features/repository_providers.dart';
import '../../../customer/presentation/customer_components.dart';

class CargoReceiptsPage extends ConsumerStatefulWidget {
  const CargoReceiptsPage({super.key});

  @override
  ConsumerState<CargoReceiptsPage> createState() => _CargoReceiptsPageState();
}

class _CargoReceiptsPageState extends ConsumerState<CargoReceiptsPage> {
  late Future<List<Map<String, dynamic>>> _receipts;
  late Future<List<Map<String, dynamic>>> _invoices;
  int _tab = 0;

  @override
  void initState() {
    super.initState();
    _receipts = ref.read(cargoOperationsRepositoryProvider).listReceipts();
    _invoices = ref.read(cargoOperationsRepositoryProvider).listInvoices();
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'CARGO COMPANY',
    title: 'Cargo · Receipts',
    notificationRoute: '/cargo/notifications',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        const CustomerHeroCard(
          eyebrow: 'Financial documents',
          title: 'Receipts & invoices',
          subtitle: 'Issue, track, and share receipts and invoices for customer bookings.',
        ),
        const SizedBox(height: 20),
        Row(
          children: [
            Expanded(
              child: FilledButton(
                onPressed: () => setState(() => _tab = 0),
                style: FilledButton.styleFrom(
                  backgroundColor: _tab == 0 ? brandCoral : appSurface,
                ),
                child: Text(
                  'Receipts',
                  style: TextStyle(color: _tab == 0 ? Colors.white : appMuted),
                ),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: FilledButton(
                onPressed: () => setState(() => _tab = 1),
                style: FilledButton.styleFrom(
                  backgroundColor: _tab == 1 ? brandCoral : appSurface,
                ),
                child: Text(
                  'Invoices',
                  style: TextStyle(color: _tab == 1 ? Colors.white : appMuted),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        FutureBuilder<List<Map<String, dynamic>>>(
          future: _tab == 0 ? _receipts : _invoices,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const CustomerSkeletonList(count: 5);
            }
            if (snapshot.hasError) {
              return CustomerEmptyState(
                icon: Icons.error_outline,
                message:
                    'Could not load ${_tab == 0 ? 'receipts' : 'invoices'}.',
                actionLabel: 'Retry',
                onAction: () => setState(() {
                  _receipts = ref
                      .read(cargoOperationsRepositoryProvider)
                      .listReceipts();
                  _invoices = ref
                      .read(cargoOperationsRepositoryProvider)
                      .listInvoices();
                }),
              );
            }
            final list = snapshot.data ?? [];
            if (list.isEmpty) {
              return CustomerEmptyState(
                icon: _tab == 0
                    ? Icons.receipt_long_outlined
                    : Icons.description_outlined,
                message: 'No ${_tab == 0 ? 'receipts' : 'invoices'} yet.',
              );
            }
            return Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: appBorder),
              ),
              child: Column(
                children: [
                  for (var i = 0; i < list.length; i++) ...[
                    _docRow(list[i], _tab == 0 ? 'RCP' : 'INV', i),
                    if (i < list.length - 1)
                      const Divider(height: 1, indent: 60),
                  ],
                ],
              ),
            );
          },
        ),
      ],
    ),
  );

  Widget _docRow(Map<String, dynamic> d, String badge, int idx) {
    final number =
        d['receipt_number'] ?? d['invoice_reference'] ?? d['reference'] ?? '—';
    final amount = d['total_amount'] ?? d['amount'] ?? 0;
    final currency = d['currency'] ?? 'TZS';
    final status = d['status'] ?? 'issued';
    final date = d['generated_at'] ?? d['due_date'] ?? d['created_at'];
    final dateText = date == null || '$date'.isEmpty
        ? 'Date unavailable'
        : '$date'.split('T').first;
    final routeId = _tab == 0
        ? d['receipt_id'] ?? d['id']
        : d['sea_booking_id'];
    return InkWell(
      onTap: routeId == null
          ? null
          : () => context.push(
              '/cargo/receipts/$routeId?type=${_tab == 0 ? 'receipt' : 'invoice'}',
            ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        child: Row(
          children: [
            Container(
              width: 40,
              height: 40,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: (idx < 2 ? brandCoral : appMuted).withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                badge,
                style: TextStyle(
                  color: idx < 2 ? brandCoral : appMuted,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    number,
                    style: const TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 15,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '$currency $amount · $dateText',
                    style: const TextStyle(color: appMuted, fontSize: 13),
                  ),
                ],
              ),
            ),
            CustomerStatusPill(label: status.toString()),
          ],
        ),
      ),
    );
  }
}
