import 'package:flutter/material.dart';

import '../../../shared/presentation/role_shell.dart';

class SuperAdminShell extends StatelessWidget {
  const SuperAdminShell({super.key});
  @override
  Widget build(BuildContext context) => const RoleShell(
    role: 'Super Admin',
    destinations: ['Home', 'Users', 'Activity', 'More'],
  );
}
