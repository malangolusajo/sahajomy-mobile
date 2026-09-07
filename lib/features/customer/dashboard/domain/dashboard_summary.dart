class CustomerDashboardSummary {
  const CustomerDashboardSummary({
    required this.shipments,
    required this.bookings,
    required this.orders,
  });

  final int shipments;
  final int bookings;
  final int orders;
}