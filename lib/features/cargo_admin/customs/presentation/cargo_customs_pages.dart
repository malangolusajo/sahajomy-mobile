import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../../customer/presentation/customer_components.dart';

class CargoCustomsDashboardPage extends StatelessWidget {
  const CargoCustomsDashboardPage({super.key});

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'CUSTOMS',
    title: 'Customs clearance',
    notificationRoute: '/cargo/notifications',
    body: ListView(padding: const EdgeInsets.fromLTRB(20, 12, 20, 28), children: [
      const CustomerHeroCard(eyebrow: 'Customs', title: 'Clearance dashboard', subtitle: 'Track customs packing lists and release status.'),
      const SizedBox(height: 20),
      Row(children: [
        Expanded(child: _metric('Pending', '2')),
        const SizedBox(width: 12),
        Expanded(child: _metric('In review', '1')),
        const SizedBox(width: 12),
        Expanded(child: _metric('Released', '8')),
      ]),
      const SizedBox(height: 24),
      const CustomerSectionHeader(title: 'Shipments'),
      const SizedBox(height: 8),
      Container(decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)), child: Column(children: [
        _shipmentRow('PL-2025-0042', 'pending', () => context.push('/cargo/customs/shipments/1')),
        const Divider(height: 1, indent: 60),
        _shipmentRow('PL-2025-0041', 'in_review', () => context.push('/cargo/customs/shipments/1')),
        const Divider(height: 1, indent: 60),
        _shipmentRow('PL-2025-0040', 'released', () => context.push('/cargo/customs/shipments/1')),
      ])),
    ]),
  );

  Widget _metric(String label, String value) => Container(padding: const EdgeInsets.all(12), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12), border: Border.all(color: appBorder)), child: Column(children: [
    Text(label, style: const TextStyle(color: appMuted, fontSize: 11)),
    const SizedBox(height: 4),
    Text(value, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 20)),
  ]));

  Widget _shipmentRow(String ref, String status, VoidCallback onTap) => InkWell(
    onTap: onTap,
    child: Padding(padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14), child: Row(children: [
      Container(width: 40, height: 40, alignment: Alignment.center, decoration: BoxDecoration(color: brandCoral.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(10)), child: const Icon(Icons.assignment, color: brandCoral)),
      const SizedBox(width: 14),
      Expanded(child: Text(ref, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15))),
      CustomerStatusPill(label: status.replaceAll('_', ' ')),
    ])),
  );
}

class CargoCustomsShipmentPage extends StatelessWidget {
  const CargoCustomsShipmentPage({required this.shipmentId, super.key});
  final String shipmentId;

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'CUSTOMS',
    title: 'Shipment detail',
    notificationRoute: '/cargo/notifications',
    body: ListView(padding: const EdgeInsets.fromLTRB(20, 12, 20, 28), children: [
      const CustomerHeroCard(eyebrow: 'Shipment', title: 'PL-2025-0042', subtitle: 'Customs packing list'),
      const SizedBox(height: 20),
      Container(padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)), child: const Column(children: [
        _Row('Status', 'Pending review'),
        Divider(),
        _Row('Cargo type', 'Sea cargo'),
        Divider(),
        _Row('Total cartons', '62'),
        Divider(),
        _Row('Total CBM', '32.4'),
      ])),
      const SizedBox(height: 24),
      OutlinedButton.icon(onPressed: () => context.push('/cargo/customs/shipments/$shipmentId/documents'), icon: const Icon(Icons.folder), label: const Text('Documents')),
      const SizedBox(height: 12),
      OutlinedButton.icon(onPressed: () => context.push('/cargo/customs/shipments/$shipmentId/update-status'), icon: const Icon(Icons.update), label: const Text('Update status')),
      const SizedBox(height: 12),
      FilledButton.icon(onPressed: () => context.push('/cargo/customs/shipments/$shipmentId/release'), icon: const Icon(Icons.check_circle), label: const Text('Release confirmation')),
    ]),
  );
}

class _Row extends StatelessWidget {
  const _Row(this.label, this.value);
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(padding: const EdgeInsets.symmetric(vertical: 8), child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
    Text(label, style: const TextStyle(color: appMuted, fontSize: 14)),
    Text(value, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
  ]));
}

class CargoCustomsDocumentsPage extends StatelessWidget {
  const CargoCustomsDocumentsPage({required this.shipmentId, super.key});
  final String shipmentId;

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'CUSTOMS',
    title: 'Documents',
    notificationRoute: '/cargo/notifications',
    body: ListView(padding: const EdgeInsets.fromLTRB(20, 12, 20, 28), children: [
      const CustomerHeroCard(eyebrow: 'Documents', title: 'Customs documents', subtitle: 'Packing list, invoice, and supporting documents.'),
      const SizedBox(height: 20),
      _doc('Packing list', 'PL-2025-0042.pdf', Icons.description),
      const SizedBox(height: 12),
      _doc('Commercial invoice', 'INV-2025-0099.pdf', Icons.receipt),
      const SizedBox(height: 12),
      _doc('Bill of lading', 'BOL-2025-0077.pdf', Icons.assignment),
    ]),
  );

  Widget _doc(String name, String file, IconData icon) => Container(padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)), child: Row(children: [
    Icon(icon, color: brandCoral, size: 28),
    const SizedBox(width: 16),
    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(name, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)), const SizedBox(height: 2), Text(file, style: const TextStyle(color: appMuted, fontSize: 12))])),
    IconButton(onPressed: () {}, icon: const Icon(Icons.download, color: brandCoral)),
  ]));
}

class CargoCustomsUpdateStatusPage extends StatefulWidget {
  const CargoCustomsUpdateStatusPage({required this.shipmentId, super.key});
  final String shipmentId;

  @override
  State<CargoCustomsUpdateStatusPage> createState() => _CargoCustomsUpdateStatusPageState();
}

class _CargoCustomsUpdateStatusPageState extends State<CargoCustomsUpdateStatusPage> {
  String _status = 'pending';

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'CUSTOMS',
    title: 'Update status',
    notificationRoute: '/cargo/notifications',
    body: ListView(padding: const EdgeInsets.fromLTRB(20, 12, 20, 28), children: [
      const CustomerHeroCard(eyebrow: 'Status', title: 'Update customs status', subtitle: 'Move this shipment through the clearance pipeline.'),
      const SizedBox(height: 24),
      DropdownButtonFormField<String>(value: _status, decoration: const InputDecoration(labelText: 'Customs status'), items: const [
        DropdownMenuItem(value: 'pending', child: Text('Pending review')),
        DropdownMenuItem(value: 'in_review', child: Text('In review')),
        DropdownMenuItem(value: 'cleared', child: Text('Cleared')),
        DropdownMenuItem(value: 'released', child: Text('Released')),
      ], onChanged: (v) => setState(() => _status = v ?? 'pending')),
      const SizedBox(height: 24),
      FilledButton(onPressed: () => context.go('/cargo/customs'), child: const Text('Update status')),
    ]),
  );
}

class CargoCustomsReleasePage extends StatelessWidget {
  const CargoCustomsReleasePage({required this.shipmentId, super.key});
  final String shipmentId;

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'CUSTOMS',
    title: 'Release confirmation',
    notificationRoute: '/cargo/notifications',
    body: ListView(padding: const EdgeInsets.fromLTRB(20, 24, 20, 28), children: [
      Column(children: [
        Container(width: 72, height: 72, decoration: BoxDecoration(color: appSuccess.withValues(alpha: 0.15), shape: BoxShape.circle), child: const Icon(Icons.verified, size: 40, color: appSuccess)),
        const SizedBox(height: 20),
        const Text('Release confirmed', style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800)),
        const SizedBox(height: 8),
        const Text('This shipment has been released by customs and is ready for collection.', textAlign: TextAlign.center, style: TextStyle(color: appMuted)),
      ]),
      const SizedBox(height: 24),
      FilledButton(onPressed: () => context.go('/cargo/customs'), child: const Text('Done')),
    ]),
  );
}
