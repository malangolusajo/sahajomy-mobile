import 'package:flutter/material.dart';

import '../../../../core/ui/sahajomy_ui.dart';
import '../../dashboard/data/cargo_admin_dashboard_repository.dart';
import '../../warehouse_automation/data/warehouse_automation_repository.dart';

class CargoAdminDocumentationWorkspacePage extends StatefulWidget {
  const CargoAdminDocumentationWorkspacePage({super.key});

  @override
  State<CargoAdminDocumentationWorkspacePage> createState() =>
      _CargoAdminDocumentationWorkspacePageState();
}

class _CargoAdminDocumentationWorkspacePageState
    extends State<CargoAdminDocumentationWorkspacePage> {
  final _repository = CargoAdminDashboardRepository();
  late Future<Map<String, dynamic>> _dashboard = _repository.loadDashboard();

  void _retry() => setState(() => _dashboard = _repository.loadDashboard());

  @override
  Widget build(BuildContext context) => FutureBuilder<Map<String, dynamic>>(
    future: _dashboard,
    builder: (context, snapshot) {
      if (snapshot.connectionState != ConnectionState.done) {
        return const Center(child: CircularProgressIndicator());
      }
      if (snapshot.hasError) {
        return SahajomyMessageState(
          icon: Icons.wifi_off_rounded,
          message: 'Cargo documentation is unavailable right now.',
          actionLabel: 'Try again',
          onAction: _retry,
        );
      }

      return ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            'Cargo documentation',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 6),
          const Text(
            'One workspace for packing lists, manual intake, and customer records.',
          ),
          const SizedBox(height: 20),
          Container(
            decoration: const BoxDecoration(
              color: Colors.white,
              border: Border.symmetric(
                vertical: BorderSide(color: Color(0xFFE2E8F0)),
              ),
            ),
            child: Column(
              children: [
                SahajomyPreviewRow(
                  title: 'Customs packing lists',
                  subtitle: 'Open the current cargo documentation flow.',
                  icon: Icons.description_outlined,
                  onTap: () => Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => const CargoAdminPackingListsPage(),
                    ),
                  ),
                ),
                SahajomyPreviewRow(
                  title: 'Manual cargo intake',
                  subtitle: 'Open the current cargo documentation flow.',
                  icon: Icons.edit_note_rounded,
                  onTap: () => Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => const CargoAdminManualIntakePage(),
                    ),
                  ),
                ),
                SahajomyPreviewRow(
                  title: 'Cargo customers',
                  subtitle: 'Open the current cargo documentation flow.',
                  icon: Icons.people_outline_rounded,
                  onTap: () => Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => const CargoAdminCustomerRecordsPage(),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          FilledButton(
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => const CargoAdminPackingListsPage(),
              ),
            ),
            child: const Text('Open packing lists'),
          ),
        ],
      );
    },
  );
}

class CargoAdminPackingListsPage extends StatefulWidget {
  const CargoAdminPackingListsPage({super.key});

  @override
  State<CargoAdminPackingListsPage> createState() =>
      _CargoAdminPackingListsPageState();
}

class _CargoAdminPackingListsPageState
    extends State<CargoAdminPackingListsPage> {
  final _repository = CargoAdminDashboardRepository();
  late Future<Map<String, dynamic>> _dashboard = _repository.loadDashboard();

  void _retry() => setState(() => _dashboard = _repository.loadDashboard());

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(
      role: 'Cargo Admin',
      title: 'Consolidated packing lists',
    ),
    body: FutureBuilder<Map<String, dynamic>>(
      future: _dashboard,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return SahajomyMessageState(
            icon: Icons.wifi_off_rounded,
            message: 'Packing lists are unavailable right now.',
            actionLabel: 'Try again',
            onAction: _retry,
          );
        }

        final dashboard = snapshot.data!;
        final actions = (dashboard['pending_actions'] as List? ?? const [])
            .cast<Map<String, dynamic>>();
        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              'Customs packing lists',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 6),
            const Text(
              'Keep export documents aligned with operational capacity and shipment readiness.',
            ),
            const SizedBox(height: 20),
            SahajomySectionCard(
              title: 'Operational checklist',
              children: [
                SahajomyKeyValueList(
                  entries: {
                    'reserved_cbm': dashboard['total_reserved_cbm'],
                    'active_containers': dashboard['active_containers'],
                    'reservations': dashboard['total_reservations'],
                  },
                ),
              ],
            ),
            const SizedBox(height: 20),
            SahajomySectionCard(
              title: 'Queues affecting documentation',
              children: [
                if (actions.isEmpty)
                  const Text(
                    'No operational blockers are delaying packing-list work.',
                  ),
                for (final action in actions)
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.task_alt_outlined),
                    title: Text(action['label'] as String? ?? 'Action'),
                    trailing: Chip(label: Text('${action['count'] ?? 0}')),
                  ),
              ],
            ),
          ],
        );
      },
    ),
  );
}

class CargoAdminReceiptsPage extends StatefulWidget {
  const CargoAdminReceiptsPage({super.key});

  @override
  State<CargoAdminReceiptsPage> createState() => _CargoAdminReceiptsPageState();
}

class _CargoAdminReceiptsPageState extends State<CargoAdminReceiptsPage> {
  final _repository = CargoAdminDashboardRepository();
  late Future<Map<String, dynamic>> _dashboard = _repository.loadDashboard();

  void _retry() => setState(() => _dashboard = _repository.loadDashboard());

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(
      role: 'Cargo Admin',
      title: 'Receipts and invoices',
    ),
    body: FutureBuilder<Map<String, dynamic>>(
      future: _dashboard,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return SahajomyMessageState(
            icon: Icons.wifi_off_rounded,
            message: 'Financial documents are unavailable right now.',
            actionLabel: 'Try again',
            onAction: _retry,
          );
        }

        final dashboard = snapshot.data!;
        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              'Receipts and invoices',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 6),
            const Text(
              'Search financial follow-ups and share authoritative documents with customers.',
            ),
            const SizedBox(height: 20),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                SahajomyMetricTile(
                  label: 'Pending payments',
                  value: dashboard['pending_payments'],
                ),
                SahajomyMetricTile(
                  label: 'Reservations',
                  value: dashboard['total_reservations'],
                ),
              ],
            ),
            const SizedBox(height: 24),
            const SahajomySectionCard(
              title: 'Document lanes',
              children: [
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(Icons.receipt_long_outlined),
                  title: Text('Recent receipts'),
                  subtitle: Text(
                    'Follow up on reservations waiting for payment confirmation.',
                  ),
                ),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(Icons.request_quote_outlined),
                  title: Text('Invoices by reservation'),
                  subtitle: Text(
                    'Use reservation and customer references to locate the authoritative PDF.',
                  ),
                ),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(Icons.share_outlined),
                  title: Text('Share and void controls'),
                  subtitle: Text(
                    'Preserve the server as the source of truth when document actions are added.',
                  ),
                ),
              ],
            ),
          ],
        );
      },
    ),
  );
}

class CargoAdminCustomerRecordsPage extends StatefulWidget {
  const CargoAdminCustomerRecordsPage({super.key});

  @override
  State<CargoAdminCustomerRecordsPage> createState() =>
      _CargoAdminCustomerRecordsPageState();
}

class _CargoAdminCustomerRecordsPageState
    extends State<CargoAdminCustomerRecordsPage> {
  final _repository = CargoAdminDashboardRepository();
  late Future<Map<String, dynamic>> _dashboard = _repository.loadDashboard();

  void _retry() => setState(() => _dashboard = _repository.loadDashboard());

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(
      role: 'Cargo Admin',
      title: 'Customer management',
    ),
    body: FutureBuilder<Map<String, dynamic>>(
      future: _dashboard,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return SahajomyMessageState(
            icon: Icons.wifi_off_rounded,
            message: 'Customer records are unavailable right now.',
            actionLabel: 'Try again',
            onAction: _retry,
          );
        }

        final dashboard = snapshot.data!;
        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              'Cargo customers',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 6),
            const Text(
              'Review operational follow-up items without bypassing shipment ownership and payment flow.',
            ),
            const SizedBox(height: 20),
            SahajomySectionCard(
              title: 'Current workload',
              children: [
                SahajomyKeyValueList(
                  entries: {
                    'active_containers': dashboard['active_containers'],
                    'reservations': dashboard['total_reservations'],
                    'pending_payments': dashboard['pending_payments'],
                    'air_bookings': dashboard['pending_air_bookings'],
                  },
                ),
              ],
            ),
            const SizedBox(height: 20),
            const SahajomySectionCard(
              title: 'Customer records flow',
              children: [
                Text(
                  '1. Find the customer by reservation, parcel, or receipt reference.',
                ),
                SizedBox(height: 8),
                Text(
                  '2. Confirm payment and documentation state before release or escalation.',
                ),
                SizedBox(height: 8),
                Text(
                  '3. Keep warehouse automation and manual intake linked back to the same customer record.',
                ),
              ],
            ),
          ],
        );
      },
    ),
  );
}

class CargoAdminManualIntakePage extends StatefulWidget {
  const CargoAdminManualIntakePage({super.key});

  @override
  State<CargoAdminManualIntakePage> createState() =>
      _CargoAdminManualIntakePageState();
}

class _CargoAdminManualIntakePageState
    extends State<CargoAdminManualIntakePage> {
  final _repository = WarehouseAutomationRepository();
  final _formKey = GlobalKey<FormState>();
  final _customerController = TextEditingController();
  final _itemController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _cartonController = TextEditingController(text: '1');
  final _weightController = TextEditingController(text: '1.0');
  final _scanTextController = TextEditingController();
  final _bookingController = TextEditingController();
  late Future<Map<String, dynamic>> _status = _repository.loadStatus();
  Map<String, dynamic>? _matchResult;
  String? _selectedWarehouseId;
  bool _matching = false;
  bool _submitting = false;

  @override
  void dispose() {
    _customerController.dispose();
    _itemController.dispose();
    _descriptionController.dispose();
    _cartonController.dispose();
    _weightController.dispose();
    _scanTextController.dispose();
    _bookingController.dispose();
    super.dispose();
  }

  void _retry() => setState(() => _status = _repository.loadStatus());

  Future<void> _previewMatch() async {
    if (_selectedWarehouseId == null ||
        _scanTextController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Choose a warehouse and enter scan text first.'),
        ),
      );
      return;
    }
    setState(() => _matching = true);
    try {
      final result = await _repository.matchIntake(
        warehouseId: _selectedWarehouseId!,
        scanText: _scanTextController.text.trim(),
      );
      if (!mounted) return;
      setState(() => _matchResult = result);
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Unable to preview the assisted intake match.'),
        ),
      );
    } finally {
      if (mounted) setState(() => _matching = false);
    }
  }

  Future<void> _confirmIntake() async {
    if (!_formKey.currentState!.validate() || _selectedWarehouseId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Complete the warehouse and intake fields first.'),
        ),
      );
      return;
    }

    setState(() => _submitting = true);
    try {
      final response = await _repository.confirmIntake({
        'warehouse_id': _selectedWarehouseId,
        'customer_id': _customerController.text.trim(),
        'cargo_type': 'parcel',
        'item_name': _itemController.text.trim(),
        'description': _descriptionController.text.trim(),
        'carton_count': int.parse(_cartonController.text.trim()),
        'weight_kg': double.parse(_weightController.text.trim()),
        'intake_method': _scanTextController.text.trim().isEmpty
            ? 'manual'
            : 'assisted_scan',
        if (_scanTextController.text.trim().isNotEmpty)
          'scan_text': _scanTextController.text.trim(),
        if (_bookingController.text.trim().isNotEmpty)
          'linked_booking_id': _bookingController.text.trim(),
      });
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Intake confirmed'),
          content: Text(
            'Reference: ${response['id'] ?? response['intake_id'] ?? 'Created successfully'}',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Close'),
            ),
          ],
        ),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Unable to confirm this intake right now.'),
        ),
      );
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(
      role: 'Cargo Admin',
      title: 'Manual cargo intake',
    ),
    body: FutureBuilder<Map<String, dynamic>>(
      future: _status,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return SahajomyMessageState(
            icon: Icons.wifi_off_rounded,
            message: 'Manual intake is unavailable right now.',
            actionLabel: 'Try again',
            onAction: _retry,
          );
        }

        final status = snapshot.data!;
        final warehouses = (status['warehouses'] as List? ?? const [])
            .cast<Map<String, dynamic>>();

        _selectedWarehouseId ??= warehouses.isNotEmpty
            ? '${warehouses.first['id']}'
            : null;

        return Form(
          key: _formKey,
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              Text(
                'Register incoming goods',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 6),
              Text(
                status['enabled'] == true
                    ? 'Automation is enabled for assisted matching, but manual intake still remains available.'
                    : 'Automation is not enabled for this operator, but manual intake remains fully available.',
              ),
              const SizedBox(height: 20),
              SahajomySectionCard(
                title: 'Intake details',
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
                    controller: _customerController,
                    decoration: const InputDecoration(
                      labelText: 'Customer UUID',
                      helperText: 'Use the authoritative customer identifier from operations.',
                    ),
                    validator: (value) =>
                        (value == null || value.trim().isEmpty)
                        ? 'Enter a customer identifier.'
                        : null,
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _itemController,
                    decoration: const InputDecoration(labelText: 'Item name'),
                    validator: (value) =>
                        (value == null || value.trim().isEmpty)
                        ? 'Enter an item name.'
                        : null,
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _descriptionController,
                    minLines: 2,
                    maxLines: 4,
                    decoration: const InputDecoration(labelText: 'Description'),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextFormField(
                          controller: _cartonController,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(
                            labelText: 'Cartons',
                          ),
                          validator: (value) =>
                              (int.tryParse(value ?? '') == null)
                              ? 'Enter a number.'
                              : null,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: TextFormField(
                          controller: _weightController,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(
                            labelText: 'Weight (kg)',
                          ),
                          validator: (value) =>
                              (double.tryParse(value ?? '') == null)
                              ? 'Enter a number.'
                              : null,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _bookingController,
                    decoration: const InputDecoration(
                      labelText: 'Linked booking UUID',
                      helperText:
                          'Optional confirmed reservation or air-booking link.',
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              SahajomySectionCard(
                title: 'Assisted scan',
                children: [
                  TextFormField(
                    controller: _scanTextController,
                    minLines: 2,
                    maxLines: 4,
                    decoration: const InputDecoration(
                      labelText: 'Scan or barcode text',
                    ),
                  ),
                  const SizedBox(height: 12),
                  OutlinedButton(
                    onPressed: _matching ? null : _previewMatch,
                    child: Text(
                      _matching ? 'Matching...' : 'Preview assisted match',
                    ),
                  ),
                  if (_matchResult != null) ...[
                    const SizedBox(height: 12),
                    SahajomyKeyValueList(
                      entries: {
                        'confidence': _matchResult!['confidence'],
                        'duplicate': _matchResult!['duplicate'],
                        'extracted_values': _matchResult!['extracted_values'],
                        'suggested_customer':
                            _matchResult!['suggested_customer'],
                      },
                    ),
                  ],
                ],
              ),
              const SizedBox(height: 20),
              FilledButton(
                onPressed: _submitting ? null : _confirmIntake,
                child: Text(
                  _submitting ? 'Confirming intake...' : 'Confirm intake',
                ),
              ),
            ],
          ),
        );
      },
    ),
  );
}
