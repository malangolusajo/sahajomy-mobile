import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:share_plus/share_plus.dart';

import '../../../../app/theme.dart';
import '../../../../features/repository_providers.dart';
import '../../presentation/customer_components.dart';

class ShippingMarkPage extends ConsumerStatefulWidget {
  const ShippingMarkPage({
    this.seaBookingId,
    this.shippingMark = const {},
    super.key,
  });
  final String? seaBookingId;
  final Map<String, dynamic> shippingMark;

  @override
  ConsumerState<ShippingMarkPage> createState() => _ShippingMarkPageState();
}

class _ShippingMarkPageState extends ConsumerState<ShippingMarkPage> {
  late Future<Map<String, dynamic>> _label = _load();

  Future<Map<String, dynamic>> _load() async {
    if (widget.seaBookingId?.isNotEmpty == true) {
      final response = await ref
          .read(customerBookingRepositoryProvider)
          .getShippingLabel(widget.seaBookingId!);
      return Map<String, dynamic>.from(response['label'] as Map? ?? response);
    }
    return widget.shippingMark;
  }

  String _shareText(Map<String, dynamic> label) => [
    'Shipping mark: ${label['shipping_mark_code'] ?? ''}',
    'Customer: ${label['customer_name'] ?? ''}',
    'Phone: ${label['customer_phone'] ?? ''}',
    'Destination: ${label['destination_region'] ?? ''}',
    'Cartons: ${label['carton_count'] ?? ''}',
    'Packing: ${label['packing_list_summary'] ?? ''}',
  ].where((line) => !line.endsWith(': ')).join('\n');

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Shipping label',
    body: FutureBuilder<Map<String, dynamic>>(
      future: _label,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError || (snapshot.data?.isEmpty ?? true)) {
          return CustomerEmptyState(
            icon: Icons.qr_code_2_rounded,
            message: 'The shipping label is unavailable.',
            actionLabel: 'Retry',
            onAction: () => setState(() => _label = _load()),
          );
        }
        final label = snapshot.data!;
        final labels = (label['labels'] as List? ?? const [])
            .whereType<Map>()
            .toList();
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          children: [
            const CustomerHeroCard(
              eyebrow: 'Official label',
              title: 'Shipping label',
              subtitle: 'Attach the matching carton label to every package.',
            ),
            const SizedBox(height: 20),
            if (labels.isEmpty)
              _PrintableLabel(label: label)
            else
              for (final raw in labels) ...[
                _PrintableLabel(label: Map<String, dynamic>.from(raw)),
                const SizedBox(height: 14),
              ],
            const SizedBox(height: 8),
            FilledButton.icon(
              onPressed: () {
                Clipboard.setData(
                  ClipboardData(text: '${label['shipping_mark_code'] ?? ''}'),
                );
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Shipping mark copied')),
                );
              },
              icon: const Icon(Icons.copy_rounded),
              label: const Text('Copy shipping mark'),
            ),
            const SizedBox(height: 10),
            OutlinedButton.icon(
              onPressed: () => SharePlus.instance.share(
                ShareParams(
                  text: _shareText(label),
                  subject:
                      'Shipping label ${label['shipping_mark_code'] ?? ''}',
                ),
              ),
              icon: const Icon(Icons.share_outlined),
              label: const Text('Share label details'),
            ),
          ],
        );
      },
    ),
  );
}

class _PrintableLabel extends StatelessWidget {
  const _PrintableLabel({required this.label});
  final Map<String, dynamic> label;

  @override
  Widget build(BuildContext context) {
    final qr = '${label['qr_payload'] ?? ''}';
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: appInk, width: 2),
      ),
      child: Column(
        children: [
          const Text(
            'SAHAJOMY SHIPPING MARK',
            style: TextStyle(
              color: brandNavy,
              fontSize: 12,
              fontWeight: FontWeight.w900,
              letterSpacing: 1.2,
            ),
          ),
          const Divider(height: 28, color: appInk),
          Text(
            '${label['shipping_mark_code'] ?? 'Not available'}',
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 27,
              fontWeight: FontWeight.w900,
              letterSpacing: 1,
            ),
          ),
          const SizedBox(height: 12),
          if (qr.isNotEmpty) QrImageView(data: qr, size: 132),
          const SizedBox(height: 12),
          _row('Customer', label['customer_name']),
          _row('Phone', label['customer_phone']),
          _row('Destination', label['destination_region']),
          _row('Carton', label['carton_label'] ?? label['carton_count']),
          _row('Packing', label['packing_list_summary']),
        ],
      ),
    );
  }

  Widget _row(String name, Object? value) {
    final text = value?.toString().trim() ?? '';
    if (text.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(top: 7),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 88,
            child: Text(
              name,
              style: const TextStyle(
                color: appMuted,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          Expanded(
            child: Text(
              text,
              style: const TextStyle(fontWeight: FontWeight.w800),
            ),
          ),
        ],
      ),
    );
  }
}
