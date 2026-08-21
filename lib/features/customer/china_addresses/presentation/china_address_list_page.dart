import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../../core/ui/sahajomy_ui.dart';
import '../data/customer_china_addresses_repository.dart';

class ChinaAddressListPage extends StatefulWidget {
  const ChinaAddressListPage({super.key});

  @override
  State<ChinaAddressListPage> createState() => _ChinaAddressListPageState();
}

class _ChinaAddressListPageState extends State<ChinaAddressListPage> {
  final _repository = CustomerChinaAddressesRepository();
  late Future<List<Map<String, dynamic>>> _addresses = _repository
      .listAddresses();

  void _retry() => setState(() => _addresses = _repository.listAddresses());

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(
      role: 'Customer',
      title: 'China addresses',
    ),
    body: FutureBuilder<List<Map<String, dynamic>>>(
      future: _addresses,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return _MessageState(
            message: 'We could not load your China addresses.',
            actionLabel: 'Try again',
            onAction: _retry,
          );
        }
        final addresses = snapshot.data ?? [];
        if (addresses.isEmpty) {
          return const _MessageState(
            message: 'Your China delivery addresses will appear here when you reserve sea or air cargo.',
          );
        }
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
          children: [
            Text(
              'My China addresses',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 6),
            const Text(
              'Use the correct warehouse address and shipping mark for every shipment.',
            ),
            const SizedBox(height: 20),
            for (final address in addresses) ...[
              _AddressCard(address: address),
              const SizedBox(height: 12),
            ],
          ],
        );
      },
    ),
  );
}

class _AddressCard extends StatelessWidget {
  const _AddressCard({required this.address});

  final Map<String, dynamic> address;

  @override
  Widget build(BuildContext context) {
    final warehouse = Map<String, dynamic>.from(
      address['warehouse'] as Map? ?? const {},
    );
    final copy = Map<String, dynamic>.from(address['copy'] as Map? ?? const {});
    final completeAddress =
        copy['complete_address'] as String? ??
        warehouse['detailed_address'] as String? ??
        'Address details unavailable.';
    final mark =
        copy['shipping_mark'] as String? ??
        address['shipping_mark'] as String? ??
        'Shipping mark';
    final mode = address['cargo_mode'] == 'air' ? 'Air cargo' : 'Sea cargo';

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.location_on_outlined,
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    warehouse['name_en'] as String? ?? 'China warehouse',
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                ),
                Chip(label: Text(mode)),
              ],
            ),
            const SizedBox(height: 12),
            Text(mark, style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            Text(completeAddress),
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerRight,
              child: OutlinedButton.icon(
                onPressed: () async {
                  await Clipboard.setData(ClipboardData(text: completeAddress));
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('China address copied.')),
                    );
                  }
                },
                icon: const Icon(Icons.copy_outlined),
                label: const Text('Copy address'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MessageState extends StatelessWidget {
  const _MessageState({required this.message, this.actionLabel, this.onAction});

  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.location_on_outlined, size: 44),
          const SizedBox(height: 14),
          Text(message, textAlign: TextAlign.center),
          if (onAction != null) ...[
            const SizedBox(height: 16),
            OutlinedButton(onPressed: onAction, child: Text(actionLabel!)),
          ],
        ],
      ),
    ),
  );
}
