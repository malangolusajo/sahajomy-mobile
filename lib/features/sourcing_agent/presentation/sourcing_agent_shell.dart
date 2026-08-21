import 'package:flutter/material.dart';

import '../../../shared/presentation/role_shell.dart';

class SourcingAgentShell extends StatelessWidget {
  const SourcingAgentShell({super.key});
  @override
  Widget build(BuildContext context) => const RoleShell(
    role: 'Sourcing Agent',
    destinations: ['Home', 'Batches', 'Orders', 'More'],
  );
}
