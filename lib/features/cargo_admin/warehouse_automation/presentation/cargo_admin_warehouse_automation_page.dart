import 'package:flutter/material.dart';

import '../../../../core/ui/sahajomy_ui.dart';
import '../../documents/presentation/cargo_admin_documentation_workspace_page.dart';
import '../data/warehouse_automation_repository.dart';

class CargoAdminWarehouseAutomationPage extends StatefulWidget {
  const CargoAdminWarehouseAutomationPage({super.key});

  @override
  State<CargoAdminWarehouseAutomationPage> createState() =>
      _CargoAdminWarehouseAutomationPageState();
}

class _CargoAdminWarehouseAutomationPageState
    extends State<CargoAdminWarehouseAutomationPage> {
  final _repository = WarehouseAutomationRepository();
  final _scanController = TextEditingController();
  final _codeController = TextEditingController();
  final _pinController = TextEditingController();
  late Future<Map<String, dynamic>> _status = _repository.loadStatus();
  String? _selectedWarehouseId;
  String? _latestAccessUrl;
  Map<String, dynamic>? _matchResult;
  Map<String, dynamic>? _collectionResult;
  bool _busy = false;
  String? _busyWarehouseId;

  @override
  void dispose() {
    _scanController.dispose();
    _codeController.dispose();
    _pinController.dispose();
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
                SahajomyKeyValueList(
                  entries: {
                    'confidence': _matchResult!['confidence'],
                    'duplicate': _matchResult!['duplicate'],
                    'extracted_values': _matchResult!['extracted_values'],
                    'suggested_customer': _matchResult!['suggested_customer'],
                    'linked_booking': _matchResult!['linked_booking'],
                  },
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
