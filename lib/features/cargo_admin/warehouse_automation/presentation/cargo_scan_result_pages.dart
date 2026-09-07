import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../../../features/repository_providers.dart';
import '../../../customer/presentation/customer_components.dart';

class _ScanResultPage extends ConsumerWidget {
  const _ScanResultPage({
    required this.title,
    required this.message,
    required this.icon,
    required this.color,
    this.result,
    this.warehouseId,
    this.showConfirm = false,
  });

  final String title;
  final String message;
  final IconData icon;
  final Color color;
  final Map<String, dynamic>? result;
  final String? warehouseId;
  final bool showConfirm;

  @override
  Widget build(BuildContext context, WidgetRef ref) => CustomerScaffold(
    eyebrow: 'WAREHOUSE',
    title: 'Scan result',
    notificationRoute: '/cargo/notifications',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 28),
      children: [
        Column(
          children: [
            Container(
              width: 72, height: 72,
              decoration: BoxDecoration(color: color.withValues(alpha: 0.15), shape: BoxShape.circle),
              child: Icon(icon, size: 40, color: color),
            ),
            const SizedBox(height: 20),
            Text(title, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w800)),
            const SizedBox(height: 8),
            Text(message, textAlign: TextAlign.center, style: const TextStyle(color: appMuted)),
          ],
        ),
        if (result != null) ...[
          const SizedBox(height: 24),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)),
            child: Column(
              children: [
                _kv('Shipping mark', result!['shipping_mark'] ?? '—'),
                const Divider(),
                _kv('Customer', result!['customer_name'] ?? result!['customer']?['name'] ?? '—'),
                const Divider(),
                _kv('Destination', '${result!['destination_country'] ?? ''} ${result!['destination_city'] ?? ''}'),
                const Divider(),
                _kv('Confidence', '${((result!['confidence'] ?? 1.0) * 100).round()}%'),
              ],
            ),
          ),
        ],
        const SizedBox(height: 24),
        if (showConfirm && result != null)
          FilledButton(
            onPressed: () async {
              try {
                await ref.read(warehouseAutomationRepositoryProvider).confirmIntake({
                  'match_id': result!['match_id'],
                  'warehouse_id': warehouseId,
                });
                if (context.mounted) context.go('/cargo');
              } catch (e) {
                if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
              }
            },
            child: const Text('Confirm intake'),
          )
        else
          FilledButton(onPressed: () => context.go('/cargo'), child: const Text('Continue')),
        const SizedBox(height: 12),
        OutlinedButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Scan again')),
      ],
    ),
  );

  Widget _kv(String label, String value) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 8),
    child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
      Text(label, style: const TextStyle(color: appMuted, fontSize: 14)),
      Text(value, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
    ]),
  );
}

class ScanMatchedPage extends StatelessWidget {
  const ScanMatchedPage({this.result, this.warehouseId, super.key});
  final Map<String, dynamic>? result;
  final String? warehouseId;

  @override
  Widget build(BuildContext context) => _ScanResultPage(
    title: 'Matched',
    message: 'The shipping mark matches a registered booking. Confirm to record the intake.',
    icon: Icons.check_circle,
    color: appSuccess,
    result: result,
    warehouseId: warehouseId,
    showConfirm: true,
  );
}

class ScanUnmatchedPage extends StatelessWidget {
  const ScanUnmatchedPage({this.result, super.key});
  final Map<String, dynamic>? result;

  @override
  Widget build(BuildContext context) => _ScanResultPage(
    title: 'No match found',
    message: 'This label does not match any registered shipping mark. Check the label or enter it manually.',
    icon: Icons.search_off,
    color: appWarning,
    result: result,
  );
}

class ScanDuplicatePage extends StatelessWidget {
  const ScanDuplicatePage({this.result, super.key});
  final Map<String, dynamic>? result;

  @override
  Widget build(BuildContext context) => _ScanResultPage(
    title: 'Already received',
    message: 'This parcel was already recorded. No duplicate intake was created.',
    icon: Icons.repeat,
    color: appWarning,
    result: result,
  );
}

class ScanLowConfidencePage extends StatelessWidget {
  const ScanLowConfidencePage({this.result, super.key});
  final Map<String, dynamic>? result;

  @override
  Widget build(BuildContext context) => _ScanResultPage(
    title: 'Low confidence',
    message: 'The scan match is below the confidence threshold. Verify the label manually before confirming.',
    icon: Icons.help_outline,
    color: appWarning,
    result: result,
  );
}

class ScanInvalidLabelPage extends StatelessWidget {
  const ScanInvalidLabelPage({super.key});

  @override
  Widget build(BuildContext context) => const _ScanResultPage(
    title: 'Invalid label',
    message: 'The scanned content is not a recognised Sahajomy shipping mark or label.',
    icon: Icons.cancel_outlined,
    color: appError,
  );
}
