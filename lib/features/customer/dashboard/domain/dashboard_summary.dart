class CustomerDashboardSummary {
  const CustomerDashboardSummary({
    required this.shipments,
    required this.reservations,
    required this.orders,
  });

  final int shipments;
  final int reservations;
  final int orders;
}
