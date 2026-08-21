import 'package:flutter/material.dart';

import '../core/auth/session.dart';
import '../core/auth/session_store.dart';
import '../features/auth/data/auth_repository.dart';
import '../features/auth/presentation/welcome_page.dart';
import '../features/cargo_admin/presentation/cargo_admin_shell.dart';
import '../features/customer/dashboard/presentation/customer_shell.dart';
import '../features/sourcing_agent/presentation/sourcing_agent_shell.dart';
import '../features/super_admin/presentation/super_admin_shell.dart';

class AppGate extends StatefulWidget {
  const AppGate({super.key});

  @override
  State<AppGate> createState() => _AppGateState();
}

class _AppGateState extends State<AppGate> {
  final _store = SessionStore();
  final _auth = AuthRepository();
  Widget? _destination;

  @override
  void initState() {
    super.initState();
    _restoreSession();
  }

  Future<void> _restoreSession() async {
    final stored = await _store.read();
    if (stored == null) {
      if (mounted) setState(() => _destination = const WelcomePage());
      return;
    }
    try {
      final verified = await _auth.verifySession(stored);
      await _store.save(verified);
      if (mounted) setState(() => _destination = _shellFor(verified.role));
    } catch (_) {
      try {
        final refreshed = await _auth.refreshSession(stored);
        await _store.save(refreshed);
        if (mounted) setState(() => _destination = _shellFor(refreshed.role));
      } catch (_) {
        await _store.clear();
        if (mounted) setState(() => _destination = const WelcomePage());
      }
    }
  }

  Widget _shellFor(UserRole role) => switch (role) {
    UserRole.customer => const CustomerShell(),
    UserRole.cargoAdmin => const CargoAdminShell(),
    UserRole.sourcingAgent => const SourcingAgentShell(),
    UserRole.superAdmin => const SuperAdminShell(),
  };

  @override
  Widget build(BuildContext context) =>
      _destination ??
      const Scaffold(body: Center(child: CircularProgressIndicator()));
}
