import 'package:flutter/material.dart';

import '../../../shared/presentation/role_shell.dart';

class CargoAdminShell extends StatelessWidget {
  const CargoAdminShell({super.key});
  @override
  Widget build(BuildContext context) => const RoleShell(
    role: 'Cargo Admin',
    destinations: ['Home', 'Operations', 'Documents', 'More'],
  );
}
