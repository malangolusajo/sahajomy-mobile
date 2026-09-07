import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../app/theme.dart';
import '../../../../features/repository_providers.dart';
import '../../presentation/customer_components.dart';

class ChinaAddressDetailPage extends ConsumerStatefulWidget {
  const ChinaAddressDetailPage({required this.addressId, super.key});

  final String addressId;

  @override
  ConsumerState<ChinaAddressDetailPage> createState() => _ChinaAddressDetailPageState();
}

class _ChinaAddressDetailPageState extends ConsumerState<ChinaAddressDetailPage> {
  late Future<Map<String, dynamic>> _address;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _address = ref
        .read(customerChinaAddressesRepositoryProvider)
        .getAddress(widget.addressId);
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'China address',
    body: FutureBuilder<Map<String, dynamic>>(
      future: _address,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return CustomerEmptyState(
            icon: Icons.error_outline,
            message: 'We could not load this China address.',
            actionLabel: 'Try again',
            onAction: () => setState(_load),
          );
        }
        final a = snapshot.data!;
        final warehouse = a['warehouse'] as Map<String, dynamic>?;
        final chineseAddress = warehouse?['address'] ?? a['warehouse_address'] ?? '—';
        final receiver = a['receiver_name'] ?? a['customer_name'] ?? '—';
        final mobile = a['receiver_phone'] ?? a['customer_phone'] ?? '—';
        final mark = a['shipping_mark'] ?? a['shipping_mark_code'] ?? '—';
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          children: [
            CustomerHeroCard(
              eyebrow: a['cargo_mode'] == 'air' ? 'Air cargo' : 'Sea cargo',
              title: '${warehouse?['name'] ?? 'Warehouse'} address',
              subtitle: 'Copy the prepared address exactly when ordering from your supplier.',
            ),
            const SizedBox(height: 24),
            Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: appBorder),
              ),
              child: Column(
                children: [
                  _addressRow('CN', 'Chinese address', '$chineseAddress', brandCoral),
                  const Divider(height: 1, indent: 60),
                  _addressRow('NM', 'Receiver', '$receiver', appMuted),
                  const Divider(height: 1, indent: 60),
                  _addressRow('PH', 'Mobile', '$mobile', appMuted),
                  const Divider(height: 1, indent: 60),
                  _addressRow('SM', 'Your shipping mark', '$mark', appMuted),
                ],
              ),
            ),
            const SizedBox(height: 20),
            FilledButton(
              onPressed: () {
                Clipboard.setData(ClipboardData(text: '$chineseAddress\n$receiver\n$mobile\n$mark'));
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Complete address copied')),
                );
              },
              child: const Text('Copy complete address'),
            ),
          ],
        );
      },
    ),
  );

  Widget _addressRow(String badge, String title, String subtitle, Color badgeColor) => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    child: Row(
      children: [
        Container(
          width: 40,
          height: 40,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: badgeColor.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Text(
            badge,
            style: TextStyle(
              color: badgeColor,
              fontSize: 13,
              fontWeight: FontWeight.w800,
            ),
          ),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
              const SizedBox(height: 2),
              Text(subtitle, style: const TextStyle(color: appMuted, fontSize: 13)),
            ],
          ),
        ),
      ],
    ),
  );
}
