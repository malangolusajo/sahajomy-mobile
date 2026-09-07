import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../../app/theme.dart';
import '../../presentation/customer_components.dart';

class ShippingMarkPage extends StatelessWidget {
  const ShippingMarkPage({this.shippingMark = const {}, super.key});

  final Map<String, dynamic> shippingMark;

  @override
  Widget build(BuildContext context) {
    final code = shippingMark['shipping_mark_code'] ?? '—';
    final destination = shippingMark['destination_region'] ?? '—';
    final cartons = shippingMark['carton_count'];
    return CustomerScaffold(
      title: 'Shipping mark',
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          const CustomerHeroCard(
            eyebrow: 'Label',
            title: 'Shipping label',
            subtitle: 'Use this mark on every carton so warehouse staff can match your goods safely.',
          ),
          const SizedBox(height: 24),
          Container(
            padding: const EdgeInsets.symmetric(vertical: 28, horizontal: 16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: appBorder),
            ),
            child: Column(
              children: [
                const Text(
                  'SAHAJOMY SHIPPING MARK',
                  style: TextStyle(
                    color: brandNavy,
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1.2,
                  ),
                ),
                const SizedBox(height: 18),
                Text(
                  code,
                  style: const TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.w900,
                    color: appInk,
                    letterSpacing: 1,
                  ),
                ),
                const SizedBox(height: 14),
                Text(
                  '${destination.toUpperCase()}${cartons != null ? ' · $cartons CARTONS' : ''}',
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: appMuted,
                    letterSpacing: 0.5,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          FilledButton(
            onPressed: () {
              Clipboard.setData(ClipboardData(text: code));
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Shipping mark copied')),
              );
            },
            child: const Text('Copy shipping mark'),
          ),
        ],
      ),
    );
  }
}
