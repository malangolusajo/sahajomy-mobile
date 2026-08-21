import 'package:flutter/material.dart';

import '../../../../core/ui/sahajomy_ui.dart';
import '../data/super_admin_warehouse_automation_repository.dart';

class SuperAdminWarehouseAutomationPage extends StatefulWidget {
  const SuperAdminWarehouseAutomationPage({super.key});

  @override
  State<SuperAdminWarehouseAutomationPage> createState() =>
      _SuperAdminWarehouseAutomationPageState();
}

class _SuperAdminWarehouseAutomationPageState
    extends State<SuperAdminWarehouseAutomationPage> {
  final _repository = SuperAdminWarehouseAutomationRepository();
  late Future<List<Map<String, dynamic>>> _cargoAdmins = _repository
      .listCargoAdmins();
  String? _savingId;

  void _reload() =>
      setState(() => _cargoAdmins = _repository.listCargoAdmins());

  Future<void> _toggle(Map<String, dynamic> cargoAdmin, bool enabled) async {
    final id = '${cargoAdmin['id']}';
    setState(() => _savingId = id);
    try {
      await _repository.setEnabled(cargoAdminId: id, enabled: enabled);
      if (!mounted) return;
      _reload();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Automation ${enabled ? 'enabled' : 'disabled'} for ${cargoAdmin['name'] ?? 'Cargo Admin'}.',
          ),
        ),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Unable to update this entitlement.')),
      );
    } finally {
      if (mounted) setState(() => _savingId = null);
    }
  }

  @override
  Widget build(BuildContext context) =>
      FutureBuilder<List<Map<String, dynamic>>>(
        future: _cargoAdmins,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return SahajomyMessageState(
              icon: Icons.wifi_off_rounded,
              message: 'Automation entitlements are unavailable right now.',
              actionLabel: 'Try again',
              onAction: _reload,
            );
          }

          final cargoAdmins = snapshot.data ?? const <Map<String, dynamic>>[];
          return ListView(
            padding: const EdgeInsets.all(20),
            children: [
              Text(
                'Warehouse automation',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 6),
              const Text(
                'Control premium tools per Cargo Admin. Manual warehouse intake always remains available.',
              ),
              const SizedBox(height: 20),
              const DecoratedBox(
                decoration: BoxDecoration(
                  color: Color(0xFFFFF2EE),
                  border: Border(
                    left: BorderSide(color: Color(0xFFFF6B4A), width: 4),
                  ),
                ),
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Future billing ready',
                        style: TextStyle(fontWeight: FontWeight.w700),
                      ),
                      SizedBox(height: 4),
                      Text(
                        'This controls a backend entitlement only. It does not charge or subscribe the operator.',
                        style: TextStyle(
                          fontSize: 12,
                          height: 1.5,
                          color: Color(0xFF475569),
                        ),
                      ),
                    ],
                  ),
                ),
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
                    if (cargoAdmins.isEmpty)
                      const Text(
                        'No Cargo Admin operators were returned by the server.',
                      ),
                    for (final cargoAdmin in cargoAdmins) ...[
                      SwitchListTile.adaptive(
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 4,
                        ),
                        value: _isEnabled(cargoAdmin),
                        onChanged: _savingId == '${cargoAdmin['id']}'
                            ? null
                            : (value) => _toggle(cargoAdmin, value),
                        title: Text(
                          cargoAdmin['name'] as String? ?? 'Cargo Admin',
                          style: const TextStyle(fontWeight: FontWeight.w800),
                        ),
                        subtitle: Text(_subtitleFor(cargoAdmin)),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          );
        },
      );
}

bool _isEnabled(Map<String, dynamic> cargoAdmin) =>
    cargoAdmin['enabled'] == true || cargoAdmin['automation_enabled'] == true;

String _subtitleFor(Map<String, dynamic> cargoAdmin) {
  final manual = cargoAdmin['manual_intake_enabled'];
  final manualLabel = manual == false ? 'Manual disabled' : 'Manual enabled';
  final automationLabel = _isEnabled(cargoAdmin)
      ? 'Automation enabled'
      : 'Automation disabled';
  return '$manualLabel · $automationLabel';
}
