import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../../../features/repository_providers.dart';
import '../../../customer/presentation/customer_components.dart';

class CargoAirSchedulesPage extends ConsumerStatefulWidget {
  const CargoAirSchedulesPage({super.key});

  @override
  ConsumerState<CargoAirSchedulesPage> createState() => _CargoAirSchedulesPageState();
}

class _CargoAirSchedulesPageState extends ConsumerState<CargoAirSchedulesPage> {
  late Future<List<Map<String, dynamic>>> _schedules;

  @override
  void initState() {
    super.initState();
    _schedules = ref.read(cargoOperationsRepositoryProvider).listAirSchedules();
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'AIR CARGO',
    title: 'Air schedules',
    notificationRoute: '/cargo/notifications',
    actions: [IconButton(onPressed: () => context.push('/cargo/air-schedules/new'), icon: const Icon(Icons.add))],
    body: ListView(padding: const EdgeInsets.fromLTRB(20, 12, 20, 28), children: [
      const CustomerHeroCard(eyebrow: 'Air cargo', title: 'Departure schedules', subtitle: 'Manage air cargo departure slots and capacity.'),
      const SizedBox(height: 20),
      FutureBuilder<List<Map<String, dynamic>>>(
        future: _schedules,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) return const CustomerSkeletonList(count: 4);
          final list = snapshot.data ?? [];
          if (list.isEmpty) return const CustomerEmptyState(icon: Icons.flight, message: 'No air schedules yet.');
          return Container(decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)), child: Column(children: [
            for (var i = 0; i < list.length; i++) ...[
              _row(list[i]),
              if (i < list.length - 1) const Divider(height: 1, indent: 60),
            ],
          ]));
        },
      ),
    ]),
  );

  Widget _row(Map<String, dynamic> s) => InkWell(
    onTap: () => context.push('/cargo/air-schedules/${s['id']}'),
    child: Padding(padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14), child: Row(children: [
      Container(width: 40, height: 40, alignment: Alignment.center, decoration: BoxDecoration(color: brandCoral.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(10)), child: const Icon(Icons.flight, color: brandCoral)),
      const SizedBox(width: 14),
      Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(s['flight_number'] ?? 'Flight', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
        const SizedBox(height: 2),
        Text('${s['origin'] ?? '—'} → ${s['destination'] ?? '—'} · ${s['departure_date'] ?? 'TBD'}', style: const TextStyle(color: appMuted, fontSize: 13)),
      ])),
      CustomerStatusPill(label: (s['status'] ?? 'open').toString()),
    ])),
  );
}

class CargoAirScheduleDetailPage extends ConsumerStatefulWidget {
  const CargoAirScheduleDetailPage({required this.scheduleId, super.key});
  final String scheduleId;

  @override
  ConsumerState<CargoAirScheduleDetailPage> createState() => _CargoAirScheduleDetailPageState();
}

class _CargoAirScheduleDetailPageState extends ConsumerState<CargoAirScheduleDetailPage> {
  late Future<Map<String, dynamic>> _schedule;

  @override
  void initState() {
    super.initState();
    _schedule = ref.read(cargoOperationsRepositoryProvider).listAirSchedules().then((l) => l.firstWhere((s) => s['id'] == widget.scheduleId, orElse: () => {}));
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'AIR CARGO',
    title: 'Schedule detail',
    notificationRoute: '/cargo/notifications',
    body: FutureBuilder<Map<String, dynamic>>(future: _schedule, builder: (context, snapshot) {
      if (snapshot.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
      final s = snapshot.data ?? {};
      return ListView(padding: const EdgeInsets.fromLTRB(20, 12, 20, 28), children: [
        CustomerHeroCard(eyebrow: 'Air cargo', title: s['flight_number'] ?? 'Flight', subtitle: '${s['origin'] ?? '—'} → ${s['destination'] ?? '—'}'),
        const SizedBox(height: 20),
        Container(padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)), child: Column(children: [
          _kv('Departure', s['departure_date']?.toString().substring(0, 10) ?? 'TBD'),
          const Divider(),
          _kv('Capacity (kg)', '${s['capacity_kg'] ?? 0}'),
          const Divider(),
          _kv('Price/kg', '${s['price_per_kg'] ?? 0}'),
          const Divider(),
          _kv('Status', (s['status'] ?? 'open').toString()),
        ])),
        const SizedBox(height: 24),
        OutlinedButton.icon(onPressed: () => context.push('/cargo/air-bookings'), icon: const Icon(Icons.airplane_ticket), label: const Text('View air bookings')),
      ]);
    }),
  );

  Widget _kv(String label, String value) => Padding(padding: const EdgeInsets.symmetric(vertical: 8), child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
    Text(label, style: const TextStyle(color: appMuted, fontSize: 14)),
    Text(value, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
  ]));
}

class CargoCreateAirSchedulePage extends ConsumerStatefulWidget {
  const CargoCreateAirSchedulePage({super.key});

  @override
  ConsumerState<CargoCreateAirSchedulePage> createState() => _CargoCreateAirSchedulePageState();
}

class _CargoCreateAirSchedulePageState extends ConsumerState<CargoCreateAirSchedulePage> {
  final _formKey = GlobalKey<FormState>();
  final _flight = TextEditingController();
  final _origin = TextEditingController();
  final _destination = TextEditingController();
  final _capacity = TextEditingController(text: '5000');
  final _price = TextEditingController(text: '5000');
  DateTime? _departure;
  bool _busy = false;

  @override
  void dispose() {
    _flight.dispose();
    _origin.dispose();
    _destination.dispose();
    _capacity.dispose();
    _price.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'AIR CARGO',
    title: 'New schedule',
    notificationRoute: '/cargo/notifications',
    body: Form(key: _formKey, child: ListView(padding: const EdgeInsets.fromLTRB(20, 12, 20, 28), children: [
      TextFormField(controller: _flight, decoration: const InputDecoration(labelText: 'Flight number'), validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null),
      const SizedBox(height: 16),
      TextFormField(controller: _origin, decoration: const InputDecoration(labelText: 'Origin airport'), validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null),
      const SizedBox(height: 16),
      TextFormField(controller: _destination, decoration: const InputDecoration(labelText: 'Destination airport'), validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null),
      const SizedBox(height: 16),
      InkWell(onTap: () async { final d = await showDatePicker(context: context, firstDate: DateTime.now(), lastDate: DateTime.now().add(const Duration(days: 365)), initialDate: DateTime.now().add(const Duration(days: 3))); setState(() => _departure = d); }, child: InputDecorator(decoration: const InputDecoration(labelText: 'Departure date'), child: Text(_departure?.toString().substring(0, 10) ?? 'Select date'))),
      const SizedBox(height: 16),
      TextFormField(controller: _capacity, decoration: const InputDecoration(labelText: 'Capacity (kg)'), keyboardType: TextInputType.number),
      const SizedBox(height: 16),
      TextFormField(controller: _price, decoration: const InputDecoration(labelText: 'Price per kg (TZS)'), keyboardType: TextInputType.number),
      const SizedBox(height: 24),
      FilledButton(onPressed: _busy ? null : _submit, child: Text(_busy ? 'Creating...' : 'Create schedule')),
    ])),
  );

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      await ref.read(cargoOperationsRepositoryProvider).createAirSchedule({
        'flight_number': _flight.text.trim(),
        'origin': _origin.text.trim(),
        'destination': _destination.text.trim(),
        'departure_date': _departure?.toIso8601String(),
        'capacity_kg': int.tryParse(_capacity.text) ?? 0,
        'price_per_kg': double.tryParse(_price.text) ?? 0,
        'currency': 'TZS',
        'status': 'open',
      });
      if (mounted) context.go('/cargo/air-schedules');
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }
}

class CargoAirBookingsPage extends ConsumerStatefulWidget {
  const CargoAirBookingsPage({super.key});

  @override
  ConsumerState<CargoAirBookingsPage> createState() => _CargoAirBookingsPageState();
}

class _CargoAirBookingsPageState extends ConsumerState<CargoAirBookingsPage> {
  late Future<List<Map<String, dynamic>>> _bookings;

  @override
  void initState() {
    super.initState();
    _bookings = ref.read(cargoOperationsRepositoryProvider).listAirBookings();
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'AIR CARGO',
    title: 'Air bookings',
    notificationRoute: '/cargo/notifications',
    body: ListView(padding: const EdgeInsets.fromLTRB(20, 12, 20, 28), children: [
      const CustomerHeroCard(eyebrow: 'Air cargo', title: 'Express air bookings', subtitle: 'Customer bookings for express air cargo.'),
      const SizedBox(height: 20),
      FutureBuilder<List<Map<String, dynamic>>>(future: _bookings, builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) return const CustomerSkeletonList(count: 4);
        final list = snapshot.data ?? [];
        if (list.isEmpty) return const CustomerEmptyState(icon: Icons.airplane_ticket, message: 'No air bookings yet.');
        return Container(decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)), child: Column(children: [
          for (var i = 0; i < list.length; i++) ...[
            InkWell(onTap: () => context.push('/cargo/air-bookings/${list[i]['id']}'), child: Padding(padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14), child: Row(children: [
              Container(width: 40, height: 40, alignment: Alignment.center, decoration: BoxDecoration(color: brandCoral.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(10)), child: const Text('AB', style: TextStyle(color: brandCoral, fontWeight: FontWeight.w800))),
              const SizedBox(width: 14),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(list[i]['reference'] ?? 'Booking', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
                const SizedBox(height: 2),
                Text('${list[i]['weight_kg'] ?? 0} kg · ${list[i]['status'] ?? 'pending'}', style: const TextStyle(color: appMuted, fontSize: 13)),
              ])),
              CustomerStatusPill(label: (list[i]['status'] ?? 'pending').toString()),
            ]))),
            if (i < list.length - 1) const Divider(height: 1, indent: 60),
          ],
        ]));
      }),
    ]),
  );
}

class CargoAirBookingDetailPage extends ConsumerStatefulWidget {
  const CargoAirBookingDetailPage({required this.bookingId, super.key});
  final String bookingId;

  @override
  ConsumerState<CargoAirBookingDetailPage> createState() => _CargoAirBookingDetailPageState();
}

class _CargoAirBookingDetailPageState extends ConsumerState<CargoAirBookingDetailPage> {
  late Future<Map<String, dynamic>> _booking;

  @override
  void initState() {
    super.initState();
    _booking = ref.read(cargoOperationsRepositoryProvider).listAirBookings().then((l) => l.firstWhere((b) => b['id'] == widget.bookingId, orElse: () => {}));
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'AIR CARGO',
    title: 'Air booking detail',
    notificationRoute: '/cargo/notifications',
    body: FutureBuilder<Map<String, dynamic>>(future: _booking, builder: (context, snapshot) {
      if (snapshot.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
      final b = snapshot.data ?? {};
      return ListView(padding: const EdgeInsets.fromLTRB(20, 12, 20, 28), children: [
        CustomerHeroCard(eyebrow: 'Air booking', title: b['reference'] ?? 'Booking', subtitle: '${b['customer_name'] ?? 'Customer'} · ${b['weight_kg'] ?? 0} kg'),
        const SizedBox(height: 20),
        Container(padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)), child: Column(children: [
          _kv('Status', (b['status'] ?? 'pending').toString()),
          const Divider(),
          _kv('Weight', '${b['weight_kg'] ?? 0} kg'),
          const Divider(),
          _kv('Amount', '${b['amount'] ?? 0} ${b['currency'] ?? 'TZS'}'),
        ])),
        const SizedBox(height: 24),
        FilledButton.icon(onPressed: () => _setStatus('confirmed'), icon: const Icon(Icons.check), label: const Text('Confirm')),
      ]);
    }),
  );

  Widget _kv(String label, String value) => Padding(padding: const EdgeInsets.symmetric(vertical: 8), child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
    Text(label, style: const TextStyle(color: appMuted, fontSize: 14)),
    Text(value, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
  ]));

  Future<void> _setStatus(String status) async {
    try {
      await ref.read(cargoOperationsRepositoryProvider).updateAirBookingStatus(widget.bookingId, status: status);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Status updated')));
        setState(() {
          _booking = ref.read(cargoOperationsRepositoryProvider).listAirBookings().then((l) => l.firstWhere((b) => b['id'] == widget.bookingId, orElse: () => {}));
        });
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    }
  }
}
