import 'package:flutter/material.dart';

import '../../../../core/ui/sahajomy_ui.dart';
import '../data/customer_warehouse_access_repository.dart';
import 'collection_code_page.dart';

class CustomerWarehouseParcelsPage extends StatefulWidget {
  const CustomerWarehouseParcelsPage({required this.opaqueToken, super.key});

  final String opaqueToken;

  @override
  State<CustomerWarehouseParcelsPage> createState() =>
      _CustomerWarehouseParcelsPageState();
}

class _CustomerWarehouseParcelsPageState
    extends State<CustomerWarehouseParcelsPage> {
  final _repository = CustomerWarehouseAccessRepository();
  late Future<Map<String, dynamic>> _access = _repository.loadParcels(
    widget.opaqueToken,
  );
  final _selected = <String>{};
  var _creating = false;

  void _retry() =>
      setState(() => _access = _repository.loadParcels(widget.opaqueToken));

  Future<void> _createCollectionRequest() async {
    setState(() => _creating = true);
    try {
      final request = await _repository.createCollectionRequest(
        opaqueToken: widget.opaqueToken,
        intakeIds: _selected.toList(),
      );
      if (!mounted) return;
      await Navigator.push<void>(
        context,
        MaterialPageRoute(builder: (_) => CollectionCodePage(request: request)),
      );
      _retry();
    } finally {
      if (mounted) setState(() => _creating = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(
      role: 'Secure warehouse access',
      title: 'My parcels',
    ),
    bottomNavigationBar: SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: FilledButton(
          onPressed: _selected.isEmpty || _creating
              ? null
              : _createCollectionRequest,
          child: Text(
            _creating
                ? 'Creating collection request...'
                : _selected.isEmpty
                ? 'Select parcels to collect'
                : 'Collect ${_selected.length} selected parcel${_selected.length == 1 ? '' : 's'}',
          ),
        ),
      ),
    ),
    body: FutureBuilder<Map<String, dynamic>>(
      future: _access,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return SahajomyMessageState(
            icon: Icons.qr_code_scanner_outlined,
            message: 'This warehouse link is unavailable or has expired.',
            actionLabel: 'Try again',
            onAction: _retry,
          );
        }
        final access = snapshot.data!;
        final parcels = (access['parcels'] as List? ?? const [])
            .cast<Map<String, dynamic>>();
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 100),
          children: [
            Text(
              '${access['warehouse_name'] ?? access['warehouse'] ?? 'Warehouse'}',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 4),
            const Text(
              'Only parcels linked to your account at this scanned warehouse are shown.',
            ),
            const SizedBox(height: 20),
            for (final parcel in parcels)
              _ParcelTile(
                parcel: parcel,
                selected: _selected.contains('${parcel['id']}'),
                onChanged: parcel['eligible_for_collection'] == true
                    ? (selected) => setState(() {
                        final id = '${parcel['id']}';
                        selected == true
                            ? _selected.add(id)
                            : _selected.remove(id);
                      })
                    : null,
              ),
          ],
        );
      },
    ),
  );
}

class _ParcelTile extends StatelessWidget {
  const _ParcelTile({
    required this.parcel,
    required this.selected,
    this.onChanged,
  });

  final Map<String, dynamic> parcel;
  final bool selected;
  final ValueChanged<bool?>? onChanged;

  @override
  Widget build(BuildContext context) => Card(
    child: CheckboxListTile(
      value: selected,
      onChanged: onChanged,
      controlAffinity: ListTileControlAffinity.leading,
      title: Text(
        '${parcel['tracking_number'] ?? parcel['reference'] ?? 'Warehouse parcel'}',
        style: const TextStyle(fontWeight: FontWeight.w800),
      ),
      subtitle: Text(
        '${parcel['shipping_mark'] ?? 'No shipping mark'} · ${parcel['weight_kg'] ?? 0} kg\n${onChanged == null ? 'Payment required or not ready for collection' : 'Paid · Ready for collection'}',
      ),
    ),
  );
}
