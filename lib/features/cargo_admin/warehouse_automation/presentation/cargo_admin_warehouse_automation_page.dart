import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:sahajomy_mobile/features/repository_providers.dart';

import '../../../../core/network/api_exception.dart';
import '../../../../core/ui/sahajomy_ui.dart';
import '../../documents/presentation/cargo_admin_documentation_workspace_page.dart';
import '../data/warehouse_automation_repository.dart';

class CargoAdminWarehouseAutomationPage extends ConsumerStatefulWidget {
  const CargoAdminWarehouseAutomationPage({super.key});

  @override
  ConsumerState<CargoAdminWarehouseAutomationPage> createState() =>
      _CargoAdminWarehouseAutomationPageState();
}

class _CargoAdminWarehouseAutomationPageState
    extends ConsumerState<CargoAdminWarehouseAutomationPage> {
  WarehouseAutomationRepository get _repository =>
      ref.read(warehouseAutomationRepositoryProvider);
  final _scanController = TextEditingController();
  final _codeController = TextEditingController();
  final _pinController = TextEditingController();
  final _customerIdController = TextEditingController();
  final _cargoTypeController = TextEditingController();
  final _itemNameController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _cartonCountController = TextEditingController();
  final _weightController = TextEditingController();
  final _bookingIdController = TextEditingController();
  late Future<Map<String, dynamic>> _status = Future.microtask(
    () => _repository.loadStatus(),
  );
  String? _selectedWarehouseId;
  String? _latestAccessUrl;
  Map<String, dynamic>? _matchResult;
  Map<String, dynamic>? _collectionResult;
  bool _busy = false;
  String? _busyWarehouseId;
  bool _labelImageSelected = false;

  @override
  void dispose() {
    _scanController.dispose();
    _codeController.dispose();
    _pinController.dispose();
    _customerIdController.dispose();
    _cargoTypeController.dispose();
    _itemNameController.dispose();
    _descriptionController.dispose();
    _cartonCountController.dispose();
    _weightController.dispose();
    _bookingIdController.dispose();
    super.dispose();
  }

  void _reload() {
    setState(() {
      _status = _repository.loadStatus();
      _latestAccessUrl = null;
    });
  }

  Future<void> _createAccessToken(String warehouseId) async {
    setState(() => _busyWarehouseId = warehouseId);
    try {
      final response = await _repository.createAccessToken(warehouseId);
      if (!mounted) return;
      setState(() => _latestAccessUrl = response['access_url'] as String?);
      _reload();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Warehouse access QR rotated.')),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Unable to rotate this warehouse QR.')),
      );
    } finally {
      if (mounted) setState(() => _busyWarehouseId = null);
    }
  }

  Future<void> _revokeAccessToken(String warehouseId) async {
    setState(() => _busyWarehouseId = warehouseId);
    try {
      await _repository.revokeAccessToken(warehouseId);
      if (!mounted) return;
      _reload();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Warehouse access QR revoked.')),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Unable to revoke this warehouse QR.')),
      );
    } finally {
      if (mounted) setState(() => _busyWarehouseId = null);
    }
  }

  Future<void> _matchIntake() async {
    if (_selectedWarehouseId == null || _scanController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Choose a warehouse and enter scan text first.'),
        ),
      );
      return;
    }
    setState(() => _busy = true);
    try {
      final result = await _repository.matchIntake(
        warehouseId: _selectedWarehouseId!,
        scanText: _scanController.text.trim(),
      );
      if (!mounted) return;
      _populateMatchFields(result);
      setState(() => _matchResult = result);
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Unable to preview this parcel scan right now.'),
        ),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _scanWithCamera() async {
    final value = await Navigator.push<String>(
      context,
      MaterialPageRoute(builder: (_) => const _BarcodeScannerPage()),
    );
    if (!mounted || value == null || value.isEmpty) return;
    _scanController.text = value;
  }

  Future<void> _chooseLabelImage() async {
    final image = await ImagePicker().pickImage(source: ImageSource.gallery);
    if (!mounted || image == null) return;
    setState(() => _labelImageSelected = true);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text(
          'Label selected. Confirm or enter its barcode text below before matching.',
        ),
      ),
    );
  }

  void _populateMatchFields(Map<String, dynamic> result) {
    final extracted = result['extracted_values'] is Map<String, dynamic>
        ? result['extracted_values'] as Map<String, dynamic>
        : const <String, dynamic>{};
    final customer = result['suggested_customer'] is Map<String, dynamic>
        ? result['suggested_customer'] as Map<String, dynamic>
        : const <String, dynamic>{};
    final booking = result['linked_booking'] is Map<String, dynamic>
        ? result['linked_booking'] as Map<String, dynamic>
        : const <String, dynamic>{};
    _customerIdController.text =
        '${customer['id'] ?? result['customer_id'] ?? ''}';
    _cargoTypeController.text =
        '${extracted['cargo_type'] ?? result['cargo_type'] ?? ''}';
    _itemNameController.text =
        '${extracted['item_name'] ?? result['item_name'] ?? ''}';
    _descriptionController.text =
        '${extracted['description'] ?? result['description'] ?? ''}';
    _cartonCountController.text =
        '${extracted['carton_count'] ?? result['carton_count'] ?? ''}';
    _weightController.text =
        '${extracted['weight_kg'] ?? result['weight_kg'] ?? ''}';
    _bookingIdController.text =
        '${booking['id'] ?? result['booking_id'] ?? ''}';
  }

  Future<void> _confirmIntake() async {
    if (_matchResult?['duplicate'] == true) return;
    if (_selectedWarehouseId == null ||
        _customerIdController.text.trim().isEmpty ||
        _itemNameController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Confirm the warehouse, customer, and item name.'),
        ),
      );
      return;
    }
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Confirm parcel intake?'),
        content: const Text(
          'This creates the canonical parcel and may update a linked booking and customer tracking.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Review again'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('Confirm intake'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;

    setState(() => _busy = true);
    try {
      final result = await _repository.confirmIntake({
        'warehouse_id': _selectedWarehouseId,
        'customer_id': _customerIdController.text.trim(),
        'cargo_type': _cargoTypeController.text.trim(),
        'item_name': _itemNameController.text.trim(),
        'description': _descriptionController.text.trim(),
        'carton_count': int.tryParse(_cartonCountController.text.trim()) ?? 0,
        'weight_kg': double.tryParse(_weightController.text.trim()) ?? 0,
        'intake_method': 'assisted_scan',
        if (_bookingIdController.text.trim().isNotEmpty)
          'booking_id': _bookingIdController.text.trim(),
      });
      if (!mounted) return;
      setState(() => _matchResult = null);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Parcel ${result['reference'] ?? result['id'] ?? ''} confirmed.',
          ),
        ),
      );
    } on ApiException catch (error) {
      if (!mounted) return;
      final message = error.isConflict
          ? 'This parcel is a duplicate or conflicts with an existing intake.'
          : error.isGone
          ? 'This intake match has expired. Scan the label again.'
          : error.message;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(message)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _verifyCollection() async {
    final code = _codeController.text.trim();
    final pin = _pinController.text.trim();
    if ((code.isEmpty && pin.isEmpty) || (code.isNotEmpty && pin.isNotEmpty)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Enter either a collection code or a PIN.'),
        ),
      );
      return;
    }
    setState(() => _busy = true);
    try {
      final result = await _repository.verifyCollection(
        code: code.isEmpty ? null : code,
        pin: pin.isEmpty ? null : pin,
      );
      if (!mounted) return;
      setState(() => _collectionResult = result);
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Unable to verify this collection request.'),
        ),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _confirmCollection() async {
    final requestId =
        '${_collectionResult?['request_id'] ?? _collectionResult?['id'] ?? ''}';
    final code = _codeController.text.trim();
    final pin = _pinController.text.trim();
    if (requestId.isEmpty) return;

    setState(() => _busy = true);
    try {
      await _repository.confirmCollection(
        requestId: requestId,
        code: code.isEmpty ? null : code,
        pin: pin.isEmpty ? null : pin,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Collection handover confirmed.')),
      );
      setState(() => _collectionResult = null);
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Unable to confirm the handover right now.'),
        ),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => FutureBuilder<Map<String, dynamic>>(
    future: _status,
    builder: (context, snapshot) {
      if (snapshot.connectionState != ConnectionState.done) {
        return const Center(child: CircularProgressIndicator());
      }
      if (snapshot.hasError) {
        return SahajomyMessageState(
          icon: Icons.wifi_off_rounded,
          message: 'Warehouse automation is unavailable right now.',
          actionLabel: 'Try again',
          onAction: _reload,
        );
      }

      final status = snapshot.data!;
      final warehouses = (status['warehouses'] as List? ?? const [])
          .cast<Map<String, dynamic>>();
      _selectedWarehouseId ??= warehouses.isNotEmpty
          ? '${warehouses.first['id']}'
          : null;
      final accessEnabled = status['enabled'] == true;
      final activeAccessCount = warehouses.where(_hasActiveAccess).length;

      return ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            'Warehouse automation',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 6),
          Text(
            accessEnabled
                ? 'Premium automation tools are enabled for this Cargo Admin.'
                : 'Automation is not enabled. Manual intake remains available.',
          ),
          const SizedBox(height: 20),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              SahajomyMetricTile(label: 'Warehouses', value: warehouses.length),
              SahajomyMetricTile(
                label: 'Active QR access',
                value: activeAccessCount,
              ),
              SahajomyMetricTile(
                label: 'Automation',
                value: accessEnabled ? 'Enabled' : 'Disabled',
              ),
            ],
          ),
          const SizedBox(height: 24),
          SahajomySectionCard(
            title: 'Warehouse QR tools',
            subtitle: 'Generate, rotate, or revoke the customer access QR for each warehouse.',
            children: [
              for (final warehouse in warehouses) ...[
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(
                    warehouse['name'] as String? ?? 'Warehouse',
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                  subtitle: Text(
                    _hasActiveAccess(warehouse)
                        ? 'Customer access QR is active.'
                        : 'No active customer access QR.',
                  ),
                  trailing: Wrap(
                    spacing: 8,
                    children: [
                      OutlinedButton(
                        onPressed: _busyWarehouseId == '${warehouse['id']}'
                            ? null
                            : () => _createAccessToken('${warehouse['id']}'),
                        child: const Text('Rotate'),
                      ),
                      if (_hasActiveAccess(warehouse))
                        OutlinedButton(
                          onPressed: _busyWarehouseId == '${warehouse['id']}'
                              ? null
                              : () => _revokeAccessToken('${warehouse['id']}'),
                          child: const Text('Revoke'),
                        ),
                    ],
                  ),
                ),
                const Divider(),
              ],
              if (_latestAccessUrl != null)
                SelectableText(
                  _latestAccessUrl!,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
            ],
          ),
          const SizedBox(height: 20),
          SahajomySectionCard(
            title: 'Assisted intake',
            subtitle: 'Preview the match from scan text before staff confirms parcel intake.',
            children: [
              DropdownButtonFormField<String>(
                initialValue: _selectedWarehouseId,
                decoration: const InputDecoration(labelText: 'Warehouse'),
                items: warehouses
                    .map(
                      (warehouse) => DropdownMenuItem<String>(
                        value: '${warehouse['id']}',
                        child: Text(
                          warehouse['name'] as String? ?? 'Warehouse',
                        ),
                      ),
                    )
                    .toList(),
                onChanged: (value) =>
                    setState(() => _selectedWarehouseId = value),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  OutlinedButton.icon(
                    onPressed: _scanWithCamera,
                    icon: const Icon(Icons.qr_code_scanner_rounded),
                    label: const Text('Scan camera'),
                  ),
                  OutlinedButton.icon(
                    onPressed: _chooseLabelImage,
                    icon: const Icon(Icons.image_outlined),
                    label: Text(
                      _labelImageSelected
                          ? 'Label selected'
                          : 'Choose label image',
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _scanController,
                minLines: 2,
                maxLines: 4,
                decoration: const InputDecoration(
                  labelText: 'Scan or barcode text',
                ),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: [
                  FilledButton(
                    onPressed: _busy ? null : _matchIntake,
                    child: Text(_busy ? 'Matching...' : 'Preview match'),
                  ),
                  OutlinedButton(
                    onPressed: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => const CargoAdminManualIntakePage(),
                      ),
                    ),
                    child: const Text('Manual intake'),
                  ),
                ],
              ),
              if (_matchResult != null) ...[
                const SizedBox(height: 12),
                SahajomyStatusPill(
                  label:
                      '${_matchResult!['confidence'] ?? 'unknown'} confidence',
                ),
                if (_matchResult!['confidence'] != 'high') ...[
                  const SizedBox(height: 8),
                  const Text(
                    'Review every suggested value. Medium and low confidence results are never confirmed automatically.',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                ],
                const SizedBox(height: 12),
                SahajomyKeyValueList(
                  entries: {
                    'confidence': _matchResult!['confidence'],
                    'duplicate': _matchResult!['duplicate'],
                    'extracted_values': _matchResult!['extracted_values'],
                    'suggested_customer': _matchResult!['suggested_customer'],
                    'linked_booking': _matchResult!['linked_booking'],
                  },
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _customerIdController,
                  decoration: const InputDecoration(labelText: 'Customer ID'),
                ),
                const SizedBox(height: 10),
                TextFormField(
                  controller: _cargoTypeController,
                  decoration: const InputDecoration(labelText: 'Cargo type'),
                ),
                const SizedBox(height: 10),
                TextFormField(
                  controller: _itemNameController,
                  decoration: const InputDecoration(labelText: 'Item name'),
                ),
                const SizedBox(height: 10),
                TextFormField(
                  controller: _descriptionController,
                  decoration: const InputDecoration(labelText: 'Description'),
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: TextFormField(
                        controller: _cartonCountController,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(labelText: 'Cartons'),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: TextFormField(
                        controller: _weightController,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(
                          labelText: 'Weight (kg)',
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                TextFormField(
                  controller: _bookingIdController,
                  decoration: const InputDecoration(
                    labelText: 'Linked booking ID (optional)',
                  ),
                ),
                const SizedBox(height: 12),
                FilledButton.icon(
                  onPressed: _busy || _matchResult!['duplicate'] == true
                      ? null
                      : _confirmIntake,
                  icon: const Icon(Icons.check_circle_outline),
                  label: Text(
                    _matchResult!['duplicate'] == true
                        ? 'Duplicate parcel'
                        : 'Confirm parcel intake',
                  ),
                ),
              ],
            ],
          ),
          const SizedBox(height: 20),
          SahajomySectionCard(
            title: 'Verify collection',
            subtitle: 'Verify the code or PIN, then confirm physical handover without auto-retrying.',
            children: [
              TextFormField(
                controller: _codeController,
                decoration: const InputDecoration(labelText: 'Collection code'),
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _pinController,
                decoration: const InputDecoration(labelText: 'Collection PIN'),
                keyboardType: TextInputType.number,
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: [
                  FilledButton(
                    onPressed: _busy ? null : _verifyCollection,
                    child: Text(_busy ? 'Verifying...' : 'Verify'),
                  ),
                  OutlinedButton(
                    onPressed: _collectionResult == null || _busy
                        ? null
                        : _confirmCollection,
                    child: const Text('Confirm handover'),
                  ),
                ],
              ),
              if (_collectionResult != null) ...[
                const SizedBox(height: 12),
                SahajomyKeyValueList(
                  entries: {
                    'request_id':
                        _collectionResult!['request_id'] ??
                        _collectionResult!['id'],
                    'parcel_count': _collectionResult!['parcel_count'],
                    'expires_at': _collectionResult!['expires_at'],
                    'payment_state': _collectionResult!['payment_state'],
                    'weights': _collectionResult!['weights'],
                  },
                ),
              ],
            ],
          ),
        ],
      );
    },
  );
}

bool _hasActiveAccess(Map<String, dynamic> warehouse) =>
    warehouse['access_token_active'] == true ||
    warehouse['has_active_access_token'] == true ||
    warehouse['access_qr_active'] == true;

class _BarcodeScannerPage extends StatefulWidget {
  const _BarcodeScannerPage();

  @override
  State<_BarcodeScannerPage> createState() => _BarcodeScannerPageState();
}

class _BarcodeScannerPageState extends State<_BarcodeScannerPage> {
  var _handled = false;

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Scan parcel label')),
    body: Stack(
      fit: StackFit.expand,
      children: [
        MobileScanner(
          onDetect: (capture) {
            if (_handled) return;
            final value = capture.barcodes
                .map((barcode) => barcode.rawValue)
                .whereType<String>()
                .firstOrNull;
            if (value == null || value.isEmpty) return;
            _handled = true;
            Navigator.pop(context, value);
          },
        ),
        Center(
          child: IgnorePointer(
            child: Container(
              width: 260,
              height: 180,
              decoration: BoxDecoration(
                border: Border.all(color: Colors.white, width: 3),
                borderRadius: BorderRadius.circular(16),
              ),
            ),
          ),
        ),
      ],
    ),
  );
}
