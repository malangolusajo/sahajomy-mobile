import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme.dart';
import '../../../customer/presentation/customer_components.dart';

class CargoStaffPage extends StatelessWidget {
  const CargoStaffPage({super.key});

  static const _staff = [
    {'name': 'Hassan J.', 'role': 'Warehouse operator', 'email': 'hassan@sahajomy.com'},
    {'name': 'Fatuma A.', 'role': 'Finance', 'email': 'fatuma@sahajomy.com'},
    {'name': 'Yusuf M.', 'role': 'Warehouse operator', 'email': 'yusuf@sahajomy.com'},
  ];

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'CARGO COMPANY',
    title: 'Staff',
    notificationRoute: '/cargo/notifications',
    actions: [IconButton(onPressed: () => context.push('/cargo/staff/new'), icon: const Icon(Icons.add))],
    body: ListView(padding: const EdgeInsets.fromLTRB(20, 12, 20, 28), children: [
      const CustomerHeroCard(eyebrow: 'Staff', title: 'Team members', subtitle: 'Manage staff access and roles.'),
      const SizedBox(height: 20),
      Container(decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)), child: Column(children: [
        for (var i = 0; i < _staff.length; i++) ...[
          _row(_staff[i]),
          if (i < _staff.length - 1) const Divider(height: 1, indent: 60),
        ],
      ])),
    ]),
  );

  Widget _row(Map<String, String> s) => Padding(padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14), child: Row(children: [
    CircleAvatar(backgroundColor: brandCoral.withValues(alpha: 0.15), child: Text(s['name']![0], style: const TextStyle(color: brandCoral, fontWeight: FontWeight.w800))),
    const SizedBox(width: 14),
    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(s['name']!, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
      const SizedBox(height: 2),
      Text(s['role']!, style: const TextStyle(color: appMuted, fontSize: 13)),
    ])),
  ]));
}

class CargoCreateStaffPage extends StatefulWidget {
  const CargoCreateStaffPage({super.key});

  @override
  State<CargoCreateStaffPage> createState() => _CargoCreateStaffPageState();
}

class _CargoCreateStaffPageState extends State<CargoCreateStaffPage> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _email = TextEditingController();
  String _role = 'warehouse_operator';

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'STAFF',
    title: 'Add staff',
    notificationRoute: '/cargo/notifications',
    body: Form(key: _formKey, child: ListView(padding: const EdgeInsets.fromLTRB(20, 12, 20, 28), children: [
      TextFormField(controller: _name, decoration: const InputDecoration(labelText: 'Full name'), validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null),
      const SizedBox(height: 16),
      TextFormField(controller: _email, decoration: const InputDecoration(labelText: 'Email'), keyboardType: TextInputType.emailAddress, validator: (v) => (v == null || !v.contains('@')) ? 'Valid email required' : null),
      const SizedBox(height: 16),
      DropdownButtonFormField<String>(initialValue: _role, decoration: const InputDecoration(labelText: 'Role'), items: const [
        DropdownMenuItem(value: 'warehouse_operator', child: Text('Warehouse operator')),
        DropdownMenuItem(value: 'finance', child: Text('Finance')),
        DropdownMenuItem(value: 'admin', child: Text('Admin')),
      ], onChanged: (v) => setState(() => _role = v ?? 'warehouse_operator')),
      const SizedBox(height: 24),
      FilledButton(onPressed: () => context.go('/cargo/staff'), child: const Text('Invite staff')),
    ])),
  );
}

class CargoBranchWorkspacePage extends StatelessWidget {
  const CargoBranchWorkspacePage({super.key});

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'WORKSPACE',
    title: 'Branch workspace',
    notificationRoute: '/cargo/notifications',
    body: ListView(padding: const EdgeInsets.fromLTRB(20, 12, 20, 28), children: [
      const CustomerHeroCard(eyebrow: 'Workspace', title: 'Dar es Salaam branch', subtitle: 'Active warehouse and staff for this branch.'),
      const SizedBox(height: 20),
      _card('Active warehouse', 'Dar es Salaam Central', Icons.warehouse),
      const SizedBox(height: 12),
      _card('Staff online', '3 / 5', Icons.people),
      const SizedBox(height: 12),
      _card('Open containers', '2', Icons.local_shipping),
    ]),
  );

  Widget _card(String label, String value, IconData icon) => Container(padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: appBorder)), child: Row(children: [
    Icon(icon, color: brandCoral, size: 28),
    const SizedBox(width: 16),
    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(label, style: const TextStyle(color: appMuted, fontSize: 13)), const SizedBox(height: 2), Text(value, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 18))])),
  ]));
}
