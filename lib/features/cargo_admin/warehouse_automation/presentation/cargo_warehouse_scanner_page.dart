import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../../../../app/theme.dart';
import '../../../../features/repository_providers.dart';

class CargoWarehouseScannerPage extends ConsumerStatefulWidget {
  const CargoWarehouseScannerPage({required this.warehouseId, super.key});

  final String warehouseId;

  @override
  ConsumerState<CargoWarehouseScannerPage> createState() => _CargoWarehouseScannerPageState();
}

class _CargoWarehouseScannerPageState extends ConsumerState<CargoWarehouseScannerPage> {
  final MobileScannerController _controller = MobileScannerController();
  bool _torch = false;
  bool _busy = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _handleScan(String value) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final result = await ref.read(warehouseAutomationRepositoryProvider).matchIntake(
        warehouseId: widget.warehouseId,
        scanText: value,
      );
      if (!mounted) return;
      final matched = result['matched'] == true;
      final duplicate = result['duplicate'] == true;
      if (matched && !duplicate) {
        context.pushReplacement('/cargo/scanner/matched', extra: result);
      } else if (duplicate) {
        context.pushReplacement('/cargo/scanner/duplicate', extra: result);
      } else {
        context.pushReplacement('/cargo/scanner/unmatched', extra: {'scan_text': value});
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Scan error: $e')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: Colors.black,
    appBar: AppBar(
      backgroundColor: Colors.black,
      foregroundColor: Colors.white,
      title: const Text('Warehouse scanner', style: TextStyle(color: Colors.white)),
      actions: [
        IconButton(
          icon: Icon(_torch ? Icons.flash_on : Icons.flash_off),
          onPressed: () {
            _controller.toggleTorch();
            setState(() => _torch = !_torch);
          },
        ),
      ],
    ),
    body: Stack(
      children: [
        MobileScanner(
          controller: _controller,
          onDetect: (capture) {
            final values = capture.barcodes.map((b) => b.rawValue).whereType<String>();
            if (values.isNotEmpty) _handleScan(values.first);
          },
        ),
        Center(
          child: Container(
            width: 260,
            height: 260,
            decoration: BoxDecoration(
              border: Border.all(color: brandCoral, width: 3),
              borderRadius: BorderRadius.circular(16),
            ),
          ),
        ),
        Positioned(
          bottom: 0,
          left: 0,
          right: 0,
          child: SafeArea(
            child: Container(
              padding: const EdgeInsets.all(20),
              color: Colors.black87,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text('Align the shipping mark or label inside the frame', textAlign: TextAlign.center, style: TextStyle(color: Colors.white70)),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton(
                          style: OutlinedButton.styleFrom(foregroundColor: Colors.white, side: const BorderSide(color: Colors.white38)),
                          onPressed: () => context.push('/cargo/scanner/manual', extra: {'warehouse_id': widget.warehouseId}),
                          child: const Text('Enter manually'),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: FilledButton(
                          onPressed: () => context.push('/cargo/scanner/choose-label', extra: {'warehouse_id': widget.warehouseId}),
                          child: const Text('Choose label image'),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    ),
  );
}
