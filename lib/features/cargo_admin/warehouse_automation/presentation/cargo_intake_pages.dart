import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../../../features/repository_providers.dart';
import '../../../customer/presentation/customer_components.dart';

class CargoManualIntakePage extends ConsumerStatefulWidget {
  const CargoManualIntakePage({this.warehouseId, super.key});

  final String? warehouseId;

  @override
  ConsumerState<CargoManualIntakePage> createState() => _CargoManualIntakePageState();
}

class _CargoManualIntakePageState extends ConsumerState<CargoManualIntakePage> {
  final _controller = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _lookup() async {
    if (_controller.text.trim().isEmpty) return;
    setState(() => _busy = true);
    try {
      final result = await ref.read(warehouseAutomationRepositoryProvider).matchIntake(
        warehouseId: widget.warehouseId ?? '',
        scanText: _controller.text.trim(),
      );
      if (!mounted) return;
      final matched = result['matched'] == true;
      if (matched) {
        context.pushReplacement('/cargo/scanner/matched', extra: result);
      } else {
        context.pushReplacement('/cargo/scanner/unmatched', extra: {'scan_text': _controller.text.trim()});
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'WAREHOUSE',
    title: 'Manual intake',
    notificationRoute: '/cargo/notifications',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        const CustomerHeroCard(
          eyebrow: 'Warehouse intake',
          title: 'Enter the shipping mark',
          subtitle: 'Type the mark exactly as printed on the parcel to look up the booking.',
        ),
        const SizedBox(height: 24),
        TextField(
          controller: _controller,
          decoration: const InputDecoration(labelText: 'Shipping mark'),
          textInputAction: TextInputAction.search,
          onSubmitted: (_) => _lookup(),
        ),
        const SizedBox(height: 24),
        FilledButton(
          onPressed: _busy ? null : _lookup,
          child: Text(_busy ? 'Looking up...' : 'Look up'),
        ),
      ],
    ),
  );
}

class CargoChooseLabelImagePage extends StatelessWidget {
  const CargoChooseLabelImagePage({this.warehouseId, super.key});
  final String? warehouseId;

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'WAREHOUSE',
    title: 'Choose label image',
    notificationRoute: '/cargo/notifications',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        const CustomerHeroCard(
          eyebrow: 'Warehouse intake',
          title: 'Upload a label image',
          subtitle: 'Select a clear photo of the shipping mark. We will match it to the booking.',
        ),
        const SizedBox(height: 24),
        Container(
          height: 200,
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)),
          child: const Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
            Icon(Icons.image_outlined, size: 48, color: appMuted),
            SizedBox(height: 8),
            Text('No image selected', style: TextStyle(color: appMuted)),
          ])),
        ),
        const SizedBox(height: 24),
        FilledButton.icon(
          onPressed: () {},
          icon: const Icon(Icons.photo_library),
          label: const Text('Select from gallery'),
        ),
        const SizedBox(height: 12),
        OutlinedButton.icon(
          onPressed: () {},
          icon: const Icon(Icons.camera_alt),
          label: const Text('Take a photo'),
        ),
      ],
    ),
  );
}

class CargoCameraPermissionPage extends StatelessWidget {
  const CargoCameraPermissionPage({super.key});

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'WAREHOUSE',
    title: 'Camera permission',
    notificationRoute: '/cargo/notifications',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 28),
      children: [
        Column(children: [
          Container(width: 72, height: 72, decoration: BoxDecoration(color: appWarning.withValues(alpha: 0.15), shape: BoxShape.circle), child: const Icon(Icons.videocam_off, size: 40, color: appWarning)),
          const SizedBox(height: 20),
          const Text('Camera access required', style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          const Text('Sahajomy needs camera access to scan shipping marks and labels.', textAlign: TextAlign.center, style: TextStyle(color: appMuted)),
        ]),
        const SizedBox(height: 24),
        FilledButton(onPressed: () {}, child: const Text('Grant camera access')),
        const SizedBox(height: 12),
        OutlinedButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Enter manually instead')),
      ],
    ),
  );
}

class CargoOfflineScanQueuePage extends StatelessWidget {
  const CargoOfflineScanQueuePage({super.key});

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'WAREHOUSE',
    title: 'Offline scan queue',
    notificationRoute: '/cargo/notifications',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        const CustomerHeroCard(eyebrow: 'Offline queue', title: 'Scans waiting to sync', subtitle: 'These scans were captured offline and will sync when connectivity returns.'),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(color: appWarning.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(12)),
          child: const Row(children: [
            Icon(Icons.cloud_off, color: appWarning),
            SizedBox(width: 10),
            Expanded(child: Text('You are offline. Scans are queued locally.', style: TextStyle(fontWeight: FontWeight.w600))),
          ]),
        ),
        const SizedBox(height: 16),
        Container(
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)),
          child: Column(children: [
            _queueRow('SAH-4829', 'Pending sync', '2 min ago'),
            const Divider(height: 1, indent: 16),
            _queueRow('SAH-1204', 'Pending sync', '5 min ago'),
          ]),
        ),
      ],
    ),
  );

  Widget _queueRow(String ref, String status, String time) => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    child: Row(children: [
      const Icon(Icons.cloud_upload, color: appMuted),
      const SizedBox(width: 12),
      Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(ref, style: const TextStyle(fontWeight: FontWeight.w700)),
        Text(time, style: const TextStyle(color: appMuted, fontSize: 12)),
      ])),
      CustomerStatusPill(label: status),
    ]),
  );
}

class CargoScanHistoryPage extends StatelessWidget {
  const CargoScanHistoryPage({super.key});

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'WAREHOUSE',
    title: 'Scan history',
    notificationRoute: '/cargo/notifications',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        const CustomerHeroCard(eyebrow: 'Scan history', title: 'Recent scans', subtitle: 'Review all scans performed at this warehouse today.'),
        const SizedBox(height: 16),
        Container(
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)),
          child: Column(children: [
            _historyRow('SAH-4829', 'Matched', '10:32', appSuccess),
            const Divider(height: 1, indent: 16),
            _historyRow('SAH-1204', 'Matched', '10:18', appSuccess),
            const Divider(height: 1, indent: 16),
            _historyRow('Unknown', 'No match', '10:05', appWarning),
          ]),
        ),
      ],
    ),
  );

  Widget _historyRow(String ref, String status, String time, Color color) => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    child: Row(children: [
      Icon(status == 'Matched' ? Icons.check_circle : Icons.cancel, color: color),
      const SizedBox(width: 12),
      Expanded(child: Text(ref, style: const TextStyle(fontWeight: FontWeight.w700))),
      Text(time, style: const TextStyle(color: appMuted, fontSize: 12)),
    ]),
  );
}
