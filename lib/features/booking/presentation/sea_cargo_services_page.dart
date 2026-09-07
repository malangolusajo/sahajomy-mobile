import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/ui/logistics_ui.dart';
import '../../../core/ui/sahajomy_ui.dart';
import '../../repository_providers.dart';
import '../data/guided_booking_repository.dart';
import 'components/booking_step_indicator.dart';
import 'components/service_selection_card.dart';

class SeaCargoServicesPage extends ConsumerStatefulWidget {
  const SeaCargoServicesPage({super.key});

  @override
  ConsumerState<SeaCargoServicesPage> createState() =>
      _SeaCargoServicesPageState();
}

class _SeaCargoServicesPageState extends ConsumerState<SeaCargoServicesPage> {
  List<Map<String, dynamic>> _services = [];
  bool _loading = true;
  String? _error;
  String _search = '';

  GuidedBookingRepository get _repo =>
      ref.read(guidedBookingRepositoryProvider);

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
      final services =
          await _repo.listSeaServices(account: BookingAccount.customer);
      if (!mounted) return;
      setState(() {
        _services = services;
        _loading = false;
      });
    } catch (error) {
      if (mounted) {
        setState(() {
          _error = logisticsError(error, 'sea freight services');
          _loading = false;
        });
      }
    }
  }

  bool _available(Map<String, dynamic> s) =>
      const ['open', 'nearly_full'].contains(s['status']) &&
      (num.tryParse('${s['available_cbm']}') ?? 0) > 0;

  String _route(Map<String, dynamic> s) =>
      '${s['route'] ?? '${s['origin'] ?? 'Origin pending'} → ${s['destination'] ?? 'Destination pending'}'}';

  void _navigateToDetails(Map<String, dynamic> service) {
    context.push(
      '/customer/booking/sea-details?container_id=${service['id']}&route=${Uri.encodeComponent(_route(service))}',
    );
  }

  @override
  Widget build(BuildContext context) {
    final matches = _services.where((s) {
      final query = _search.toLowerCase();
      return '${_route(s)} ${s['operator'] ?? ''} ${s['operator_name'] ?? ''}'
          .toLowerCase()
          .contains(query);
    }).toList();

    return Scaffold(
      appBar: const SahajomyScreenHeader(
        role: 'Customer',
        title: 'Sea cargo services',
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(24, 16, 24, 32),
        children: [
          const BookingStepIndicator(
            steps: ['Service', 'Cargo details', 'Review'],
            currentStep: 0,
          ),
          const SizedBox(height: 24),
          const LogisticsIntro(
            eyebrow: 'Step 1 of 3',
            title: 'Choose your sailing',
            description:
                'Compare cargo companies, available space and published rates.',
          ),
          const SizedBox(height: 16),
          TextField(
            onChanged: (value) => setState(() => _search = value),
            decoration: const InputDecoration(
              labelText: 'Search origin, destination or company',
              prefixIcon: Icon(Icons.search),
            ),
          ),
          const SizedBox(height: 20),
          if (_loading)
            const Center(child: CircularProgressIndicator())
          else if (_error != null && _services.isEmpty)
            SahajomyMessageState(
              icon: Icons.cloud_off_outlined,
              message: _error!,
              actionLabel: 'Reload',
              onAction: _load,
            )
          else if (matches.isEmpty)
            const SahajomyMessageState(
              icon: Icons.directions_boat_outlined,
              message: 'No sailings match your search.',
            )
          else
            for (final service in matches)
              _ServiceCard(
                service: service,
                route: _route(service),
                available: _available(service),
                onSelected: _navigateToDetails,
              ),
        ],
      ),
    );
  }
}

class _ServiceCard extends StatelessWidget {
  const _ServiceCard({
    required this.service,
    required this.route,
    required this.available,
    required this.onSelected,
  });

  final Map<String, dynamic> service;
  final String route;
  final bool available;
  final void Function(Map<String, dynamic>) onSelected;

  @override
  Widget build(BuildContext context) {
    final VoidCallback? tapHandler =
        available ? () => onSelected(service) : null;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: ServiceSelectionCard(
        title:
            '${service['operator'] ?? service['operator_name'] ?? 'Cargo company'}',
        route: route,
        availableText: '${service['available_cbm'] ?? '—'} CBM available',
        statusText: '${service['status'] ?? 'Status unavailable'}',
        priceText:
            '${service['price_per_cbm'] ?? 'Rate pending'} ${service['currency'] ?? ''} / CBM',
        isRecommended: service['is_recommended'] == true,
        departureDate: service['departure_date'] != null
            ? logisticsDate(service['departure_date'])
            : null,
        onTap: tapHandler,
      ),
    );
  }
}
