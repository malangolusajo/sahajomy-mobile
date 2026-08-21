enum UserRole { customer, cargoAdmin, sourcingAgent, superAdmin }

UserRole userRoleFromApi(String value) => switch (value) {
  'customer' => UserRole.customer,
  'cargo_admin' => UserRole.cargoAdmin,
  'sourcing_agent' => UserRole.sourcingAgent,
  'super_admin' => UserRole.superAdmin,
  _ => throw FormatException('Unsupported user role: $value'),
};

class Session {
  const Session({
    required this.accessToken,
    required this.refreshToken,
    required this.role,
  });

  final String accessToken;
  final String refreshToken;
  final UserRole role;
}
