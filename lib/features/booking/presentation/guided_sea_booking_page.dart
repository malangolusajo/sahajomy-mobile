import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/network/api_exception.dart';
import '../../../core/ui/sahajomy_ui.dart';
import '../../repository_providers.dart';
import '../data/guided_booking_repository.dart';

class GuidedSeaBookingPage extends ConsumerStatefulWidget {
  const GuidedSeaBookingPage({
    required this.account,
    this.initialContainerId,
    super.key,
  });

  final BookingAccount account;
  final String? initialContainerId;

  @override
  ConsumerState<GuidedSeaBookingPage> createState() =>
      _GuidedSeaBookingPageState();
}

class _GuidedSeaBookingPageState extends ConsumerState<GuidedSeaBookingPage> {
  final _detailsKey = GlobalKey<FormState>();
  final _searchController = TextEditingController();
  final _cbmController = TextEditingController();
  final _destinationController = TextEditingController();
  final _cartonController = TextEditingController();
  Timer? _searchDebounce;
  List<Map<String, dynamic>> _services = const [];
  Map<String, dynamic>? _selectedService;
  Map<String, dynamic>? _preparedAddress;
  Map<String, dynamic>? _confirmation;
  String? _message;
  var _step = 0;
  var _page = 1;
  var _loading = true;
  var _loadingMore = false;
  var _browseAll = false;
  var _confirming = false;

  GuidedBookingRepository get _repository =>
      ref.read(guidedBookingRepositoryProvider);
  bool get _isCustomer => widget.account == BookingAccount.customer;
  String get _role => _isCustomer ? 'Customer' : 'Sourcing Agent';

  @override
  void initState() {
    super.initState();
    Future.microtask(_loadInitial);
  }

  @override
  void dispose() {
    _searchDebounce?.cancel();
    _searchController.dispose();
    _cbmController.dispose();
    _destinationController.dispose();
    _cartonController.dispose();
    super.dispose();
  }

  Future<void> _loadInitial() async {
    setState(() {
      _loading = true;
      _message = null;
    });
    try {
      final services = await _repository.listSeaServices(
        account: widget.account,
      );
      if (!mounted) return;
      setState(() {
        _services = services;
        _loading = false;
      });
      final initialId = widget.initialContainerId;
      if (initialId != null && initialId.isNotEmpty) {
        final matches = services.where((service) => _id(service) == initialId);
        if (matches.isEmpty) {
          setState(() {
            _message = 'That container is no longer available. Choose another service.';
          });
        } else {
          await _selectService(matches.first);
        }
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _loading = false;
          _message =
              'Services are unavailable. Check your connection and retry.';
        });
      }
    }
  }

  void _searchChanged(String _) {
    _searchDebounce?.cancel();
    _searchDebounce = Timer(const Duration(milliseconds: 350), _runSearch);
  }

  Future<void> _runSearch() async {
    setState(() {
      _loading = true;
      _page = 1;
    });
    try {
      final services = await _repository.listSeaServices(
        account: widget.account,
        search: _searchController.text,
      );
      if (mounted) setState(() => _services = services);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _loadMore() async {
    if (_loadingMore) return;
    setState(() => _loadingMore = true);
    try {
      final nextPage = _page + 1;
      final services = await _repository.listSeaServices(
        account: widget.account,
        page: nextPage,
        search: _searchController.text,
      );
      if (!mounted) return;
      setState(() {
        _page = nextPage;
        final known = _services.map(_id).toSet();
        _services = [
          ..._services,
          ...services.where((service) => known.add(_id(service))),
        ];
      });
    } finally {
      if (mounted) setState(() => _loadingMore = false);
    }
  }

  Future<void> _selectService(Map<String, dynamic> service) async {
    if (_loading) return;
    setState(() {
      _loading = true;
      _message = 'Preparing the operator China address…';
    });
    try {
      final address = await _repository.prepareSeaAddress(
        containerId: _id(service),
      );
      if (!mounted) return;
      setState(() {
        _selectedService = service;
        _preparedAddress = address;
        _step = 1;
        _message = null;
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _message = error.isGone || error.statusCode == 404
            ? 'That service is stale or inaccessible. Choose another service.'
            : error.message;
      });
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _continueToReview() {
    if (!_detailsKey.currentState!.validate()) return;
    setState(() => _step = 2);
  }

  Future<void> _confirm() async {
    if (_confirming || _selectedService == null) return;
    setState(() => _confirming = true);
    try {
      final response = await _repository.confirmSeaBooking(
        account: widget.account,
        payload: {
          'container_id': _id(_selectedService!),
          'reserved_cbm': double.parse(_cbmController.text.trim()),
          'destination_region': _destinationController.text.trim(),
          'carton_count': int.tryParse(_cartonController.text.trim()),
          if (_preparedAddress?['id'] != null)
            'prepared_address_id': _preparedAddress!['id'],
        },
      );
      if (mounted) setState(() => _confirmation = response);
    } on ApiException catch (error) {
      if (mounted) setState(() => _message = error.message);
    } finally {
      if (mounted) setState(() => _confirming = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: SahajomyScreenHeader(role: _role, title: 'Book sea cargo'),
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 18, 20, 28),
      children: [
        _Progress(step: _confirmation == null ? _step : 3),
        const SizedBox(height: 22),
        if (_message != null) ...[
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFFFFF7ED),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(_message!),
          ),
          const SizedBox(height: 16),
        ],
        if (_confirmation != null)
          _confirmed()
        else if (_step == 0)
          _chooseService()
        else if (_step == 1)
          _cargoDetails()
        else
          _review(),
      ],
    ),
  );

  Widget _chooseService() {
    final visible = _browseAll ? _services : _services.take(3).toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'Choose service',
          style: Theme.of(context).textTheme.headlineMedium,
        ),
        const SizedBox(height: 6),
        const Text(
          'Start with a recommended route or browse the full catalogue.',
        ),
        if (_browseAll) ...[
          const SizedBox(height: 16),
          TextField(
            controller: _searchController,
            onChanged: _searchChanged,
            decoration: const InputDecoration(
              labelText: 'Search services',
              prefixIcon: Icon(Icons.search),
            ),
          ),
        ],
        const SizedBox(height: 16),
        if (_loading)
          const Center(child: CircularProgressIndicator())
        else if (visible.isEmpty)
          const SahajomyMessageState(
            icon: Icons.directions_boat_outlined,
            message: 'No sea services match your search.',
          )
        else
          for (final service in visible) ...[
            Card(
              margin: const EdgeInsets.only(bottom: 10),
              child: ListTile(
                minTileHeight: 72,
                title: Text(
                  '${service['origin'] ?? 'China'} → ${service['destination'] ?? service['destination_region'] ?? 'Destination'}',
                  style: const TextStyle(fontWeight: FontWeight.w800),
                ),
                subtitle: Text(
                  '${service['cargo_admin_name'] ?? service['operator_name'] ?? service['company_name'] ?? 'Cargo operator'} · ${service['available_cbm'] ?? 'Available'} CBM',
                ),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => _selectService(service),
              ),
            ),
          ],
        if (!_browseAll)
          OutlinedButton(
            onPressed: () => setState(() => _browseAll = true),
            child: const Text('Browse all services'),
          )
        else
          OutlinedButton(
            onPressed: _loadingMore ? null : _loadMore,
            child: Text(_loadingMore ? 'Loading…' : 'Load more'),
          ),
      ],
    );
  }

  Widget _cargoDetails() => Form(
    key: _detailsKey,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'Cargo details',
          style: Theme.of(context).textTheme.headlineMedium,
        ),
        const SizedBox(height: 6),
        Text(
          '${_selectedService?['origin'] ?? 'China'} → ${_selectedService?['destination'] ?? 'Destination'}',
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 16),
        SahajomySectionCard(
          title: 'Operator China address',
          children: [
            Text(
              '${_preparedAddress?['formatted_address'] ?? _preparedAddress?['address'] ?? 'Prepared securely for this booking'}',
            ),
          ],
        ),
        const SizedBox(height: 16),
        TextFormField(
          controller: _cbmController,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: const InputDecoration(labelText: 'Volume (CBM)'),
          validator: (value) => (double.tryParse(value ?? '') ?? 0) <= 0
              ? 'Enter a volume greater than zero.'
              : null,
        ),
        const SizedBox(height: 12),
        TextFormField(
          controller: _destinationController,
          decoration: const InputDecoration(labelText: 'Destination region'),
          validator: (value) => value == null || value.trim().isEmpty
              ? 'Enter the destination region.'
              : null,
        ),
        const SizedBox(height: 12),
        TextFormField(
          controller: _cartonController,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'Carton count'),
        ),
        const SizedBox(height: 20),
        FilledButton(
          onPressed: _continueToReview,
          child: const Text('Continue to review'),
        ),
        TextButton(
          onPressed: () => setState(() => _step = 0),
          child: const Text('Change service'),
        ),
      ],
    ),
  );

  Widget _review() => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Text('Review booking', style: Theme.of(context).textTheme.headlineMedium),
      const SizedBox(height: 6),
      const Text(
        'No booking has been created yet. Confirm only after checking every detail.',
      ),
      const SizedBox(height: 18),
      SahajomySectionCard(
        title: 'Booking summary',
        children: [
          SahajomyKeyValueList(
            entries: {
              'service':
                  '${_selectedService?['origin'] ?? 'China'} → ${_selectedService?['destination'] ?? 'Destination'}',
              'volume': '${_cbmController.text} CBM',
              'destination': _destinationController.text,
              'cartons': _cartonController.text.isEmpty
                  ? 'Not provided'
                  : _cartonController.text,
              if (_isCustomer)
                'shipping mark':
                    _preparedAddress?['shipping_mark'] ??
                    'Assigned by operator',
            },
          ),
          if (_isCustomer)
            TextButton(
              onPressed: () => context.push('/customer/china-addresses'),
              child: const Text('Open My China Addresses'),
            ),
        ],
      ),
      const SizedBox(height: 20),
      FilledButton(
        onPressed: _confirming ? null : _confirm,
        child: Text(_confirming ? 'Confirming…' : 'Confirm booking'),
      ),
      TextButton(
        onPressed: _confirming ? null : () => setState(() => _step = 1),
        child: const Text('Edit cargo details'),
      ),
    ],
  );

  Widget _confirmed() {
    final reference =
        _confirmation?['reference'] ??
        _confirmation?['booking_reference'] ??
        _confirmation?['id'] ??
        'Confirmed';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Icon(Icons.check_circle, color: Color(0xFF059669), size: 64),
        const SizedBox(height: 12),
        Text(
          'Booking confirmed',
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.headlineMedium,
        ),
        const SizedBox(height: 18),
        SahajomySectionCard(
          title: '$reference',
          children: [
            SahajomyKeyValueList(
              entries: {
                'status': _confirmation?['status'] ?? 'Confirmed',
                'volume': '${_cbmController.text} CBM',
                'China address':
                    _preparedAddress?['formatted_address'] ??
                    _preparedAddress?['address'] ??
                    'Prepared by operator',
              },
            ),
          ],
        ),
        const SizedBox(height: 20),
        FilledButton(
          onPressed: () => context.pop(),
          child: const Text('View bookings'),
        ),
        OutlinedButton(
          onPressed: () => setState(() {
            _step = 0;
            _confirmation = null;
            _selectedService = null;
            _preparedAddress = null;
          }),
          child: const Text('Book another'),
        ),
      ],
    );
  }

  String _id(Map<String, dynamic> service) =>
      '${service['id'] ?? service['container_id'] ?? ''}';
}

class _Progress extends StatelessWidget {
  const _Progress({required this.step});
  final int step;

  @override
  Widget build(BuildContext context) => Row(
    children: [
      for (var index = 0; index < 3; index++) ...[
        Expanded(
          child: Column(
            children: [
              Icon(
                index < step
                    ? Icons.check_circle
                    : index == step
                    ? Icons.radio_button_checked
                    : Icons.radio_button_unchecked,
                color: index <= step
                    ? const Color(0xFFFF6B4A)
                    : const Color(0xFF94A3B8),
              ),
              const SizedBox(height: 4),
              Text(
                const ['Service', 'Cargo', 'Review'][index],
                style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ),
        if (index < 2)
          Expanded(
            child: Divider(
              color: index < step
                  ? const Color(0xFFFF6B4A)
                  : const Color(0xFFE2E8F0),
            ),
          ),
      ],
    ],
  );
}
