import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../../customer/presentation/customer_components.dart';

class CargoWarehouseQrPage extends StatelessWidget {
  const CargoWarehouseQrPage({required this.warehouseId, super.key});
  final String warehouseId;

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'WAREHOUSE',
    title: 'Warehouse QR',
    notificationRoute: '/cargo/notifications',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        const CustomerHeroCard(
          eyebrow: 'Warehouse identity',
          title: 'Scan to access this warehouse',
          subtitle: 'Staff and approved devices can scan this QR to enter the warehouse workspace.',
        ),
        const SizedBox(height: 24),
        Center(
          child: Container(
            width: 260, height: 260,
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)),
            child: Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: appInk, width: 2),
              ),
              child: CustomPaint(painter: _QrPainter()),
            ),
          ),
        ),
        const SizedBox(height: 24),
        FilledButton.icon(onPressed: () => context.push('/cargo/warehouses/$warehouseId/qr/fullscreen'), icon: const Icon(Icons.fullscreen), label: const Text('Fullscreen')),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(child: OutlinedButton.icon(onPressed: () {}, icon: const Icon(Icons.rotate_90_degrees_cw), label: const Text('Rotate'))),
            const SizedBox(width: 10),
            Expanded(child: OutlinedButton.icon(onPressed: () => context.push('/cargo/warehouses/$warehouseId/qr/revoked'), icon: const Icon(Icons.refresh), label: const Text('Rotate code'))),
          ],
        ),
      ],
    ),
  );
}

class CargoWarehouseQrFullscreenPage extends StatelessWidget {
  const CargoWarehouseQrFullscreenPage({super.key});

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: Colors.white,
    body: SafeArea(
      child: Column(
        children: [
          Align(alignment: Alignment.topLeft, child: IconButton(icon: const Icon(Icons.close), onPressed: () => Navigator.of(context).pop())),
          Expanded(child: Center(child: Container(width: 320, height: 320, padding: const EdgeInsets.all(24), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)), child: CustomPaint(painter: _QrPainter())))),
        ],
      ),
    ),
  );
}

class CargoWarehouseQrRevokedPage extends StatelessWidget {
  const CargoWarehouseQrRevokedPage({super.key});

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'WAREHOUSE',
    title: 'QR rotated',
    notificationRoute: '/cargo/notifications',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 28),
      children: [
        Column(children: [
          Container(width: 72, height: 72, decoration: BoxDecoration(color: appSuccess.withValues(alpha: 0.15), shape: BoxShape.circle), child: const Icon(Icons.refresh, size: 40, color: appSuccess)),
          const SizedBox(height: 20),
          const Text('Access code rotated', style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          const Text('The previous QR has been revoked. A fresh code is now active.', textAlign: TextAlign.center, style: TextStyle(color: appMuted)),
        ]),
        const SizedBox(height: 24),
        FilledButton(onPressed: () => context.go('/cargo'), child: const Text('Continue')),
      ],
    ),
  );
}

class _QrPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = appInk;
    final cell = size.width / 25;
    final rng = List.generate(625, (i) => (i * 7 + 13) % 3 == 0);
    for (var y = 0; y < 25; y++) {
      for (var x = 0; x < 25; x++) {
        final isCorner = (x < 7 && y < 7) || (x > 17 && y < 7) || (x < 7 && y > 17);
        if (rng[y * 25 + x] || isCorner) {
          canvas.drawRect(Rect.fromLTWH(x * cell, y * cell, cell, cell), paint);
        }
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
