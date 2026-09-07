import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/ui/logistics_ui.dart';
import '../../../core/ui/sahajomy_ui.dart';
import '../../customer/presentation/customer_components.dart';
import '../../repository_providers.dart';
import '../../customer/air_cargo/data/customer_air_cargo_repository.dart';
import 'components/booking_step_indicator.dart';
import 'components/service_selection_card.dart';

class AirCargoServicesPage extends ConsumerStatefulWidget {
  const AirCargoServicesPage({super.key});

  @override
  ConsumerState<AirCargoServicesPage> createState() =>
      _AirCargoServicesPageState();
}

class _AirCargoServicesPageState extends ConsumerState<AirCargoServicesPage> {
  List<Map<String, dynamic>> _services = [];
  bool _loading = true;
  String? _error;
  String _search = '';

  CustomerAirCargoRepository get _repo =>
      ref.read(customerAirCargoRepositoryProvider);

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final options = await _repo.options();
      if (!mounted) return;
      final services = (options['services'] as List? ?? const [])
          .whereType<Map>()
          .map((s) => Map<String, dynamic>.from(s))
          .toList();
      setState(() {
        _services = services;
        _loading = false;
      });
    } catch (error) {
      if (mounted) {
        setState(() {
          _error = logisticsError(error, 'air cargo services');
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final matches = _services.where((s) {
      final query = _search.toLowerCase();
      return '${s['cargo_admin_name'] ?? ''} ${s['warehouse_name'] ?? ''}'
          .toLowerCase()
          .contains(query);
    }).toList();

    return CustomerScaffold(
      title: 'Air cargo services',
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
        children: [
          const CustomerHeroCard(
            eyebrow: 'Air cargo',
            title: 'Choose your air cargo service',
            subtitle: 'Select a cargo company and China warehouse for your express air shipment.',
          ),
          const SizedBox(height: 20),
          const BookingStepIndicator(
            steps: ['Service', 'Cargo details', 'Review'],
            currentStep: 0,
          ),
          const SizedBox(height: 20),
          TextField(
            onChanged: (value) => setState(() => _search = value),
            decoration: const InputDecoration(
              labelText: 'Search cargo company or warehouse',
              prefixIcon: Icon(Icons.search),
            ),
          ),
          const SizedBox(height: 20),
          if (_loading)
            const CustomerSkeletonList()
          else if (_error != null && _services.isEmpty)
            SahajomyMessageState(
              icon: Icons.cloud_off_outlined,
              message: _error!,
              actionLabel: 'Reload',
              onAction: _load,
            )
          else if (matches.isEmpty)
            const CustomerEmptyState(
              icon: Icons.flight_outlined,
              message: 'No air cargo services available right now.',
            )
          else
            for (final service in matches)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: ServiceSelectionCard(
                  title: service['cargo_admin_name'] ?? 'Cargo company',
                  operator: service['warehouse_name'],
                  route: 'Express Air Cargo',
                  availableText: 'Available',
                  statusText: 'Active',
                  priceText: 'Quotation required',
                  onTap: () => context.push(
                    '/customer/booking/air-details'
                    '?warehouse_id=${service['warehouse_id']}'
                    '&cargo_admin_id=${service['cargo_admin_id']}'
                    '&company_name=${Uri.encodeComponent(service['cargo_admin_name'] ?? '')}'
                    '&warehouse_name=${Uri.encodeComponent(service['warehouse_name'] ?? '')}',
                  ),
                ),
              ),
        ],
      ),
    );
  }
}
