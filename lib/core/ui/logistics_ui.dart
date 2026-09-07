import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../app/theme.dart';
import '../network/api_exception.dart';
import 'sahajomy_ui.dart';

String logisticsError(Object? error, String subject) {
  if (error is ApiException) {
    if (error.isUnauthorized) return 'Sign in again to view $subject.';
    if (error.isForbidden) return 'Your current workspace does not have access to $subject.';
    if (error.statusCode == 404 || error.isGone) return 'This $subject is no longer available.';
    if (error.isValidationError) return 'Review the required details and try again.';
    if (error.isConflict) return 'These details have changed. Refresh before trying again.';
    if (error.isRateLimited) return 'Please wait a moment before trying again.';
  }
  return 'We could not load $subject. Check your connection and try again.';
}

String logisticsDate(Object? value) {
  final date = DateTime.tryParse(value?.toString() ?? '');
  return date == null ? 'Date not provided' : DateFormat('d MMM yyyy').format(date.toLocal());
}

/// Only approved display fields are shown. IDs used for routing are never used
/// as a substitute for operational references, and arbitrary JSON is not shown.
const logisticsFields = <String, String>{
  'tracking_number': 'Tracking number', 'booking_reference': 'Booking reference',
  'order_number': 'Order number', 'invoice_number': 'Invoice number',
  'receipt_number': 'Receipt number', 'container_number': 'Container number',
  'name': 'Name', 'title': 'Title', 'description': 'Description',
  'order_description': 'Cargo description', 'cargo_description': 'Cargo description',
  'route': 'Shipping route', 'origin': 'Origin', 'destination': 'Destination',
  'destination_region': 'Destination city', 'destination_country': 'Destination country',
  'status': 'Status', 'payment_status': 'Payment status', 'goods_status': 'Cargo status',
  'delivery_status': 'Delivery status', 'supplier_name': 'Supplier',
  'customer_name': 'Customer', 'cargo_admin_name': 'Cargo company', 'operator_name': 'Cargo company',
  'warehouse_name': 'Warehouse', 'shipping_mark': 'Shipping mark',
  'cbm_booked': 'Booked volume (CBM)', 'booked_cbm': 'Booked volume (CBM)',
  'available_cbm': 'Available volume (CBM)', 'max_cbm': 'Capacity (CBM)',
  'weight_kg': 'Weight (kg)', 'gross_weight': 'Gross weight', 'chargeable_weight': 'Chargeable weight',
  'carton_count': 'Cartons', 'quantity': 'Quantity', 'items_count': 'Items',
  'price_per_cbm': 'Rate per CBM', 'price': 'Price', 'unit_price': 'Unit price',
  'logistics_charge': 'Freight charge', 'total_amount': 'Total amount',
  'amount': 'Amount', 'currency': 'Currency', 'balance': 'Balance',
  'departure_date': 'Estimated departure', 'estimated_arrival_date': 'Estimated arrival',
  'arrival_date': 'Arrival', 'shipment_date': 'Shipment date', 'created_at': 'Created',
  'latest_update': 'Latest shipment update', 'current_location': 'Current location',
  'email': 'Email address', 'phone': 'Phone', 'phone_number': 'Mobile number',
  'address': 'Address', 'city': 'City', 'country': 'Country', 'container_size': 'Container size',
  'total_users': 'Accounts', 'total_bookings': 'Cargo bookings', 'total_containers': 'Containers',
  'total_shipments': 'Shipments', 'total_revenue': 'Revenue', 'total_orders': 'Orders',
};

Map<String, Object?> logisticsDetails(Map<String, dynamic> record) => {
  for (final field in logisticsFields.entries)
    if (record[field.key] != null && record[field.key] is! Map && record[field.key] is! List)
      field.value: field.key.endsWith('_date') || field.key == 'created_at'
          ? logisticsDate(record[field.key])
          : field.key.contains('status')
          ? sahajomyTitleCase('${record[field.key]}')
          : record[field.key],
};

class LogisticsIntro extends StatelessWidget {
  const LogisticsIntro({required this.title, required this.description, this.eyebrow, this.action, super.key});
  final String title;
  final String description;
  final String? eyebrow;
  final Widget? action;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 24),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      if (eyebrow != null) ...[
        Text(eyebrow!.toUpperCase(), style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 1.6, color: brandTeal)),
        const SizedBox(height: 10),
      ],
      Text(title, style: Theme.of(context).textTheme.headlineMedium),
      const SizedBox(height: 8),
      Text(description),
      if (action != null) ...[const SizedBox(height: 18), action!],
    ]),
  );
}

class LogisticsRecordTile extends StatelessWidget {
  const LogisticsRecordTile({required this.record, required this.subject, this.onTap, this.icon = Icons.local_shipping_outlined, super.key});
  final Map<String, dynamic> record;
  final String subject;
  final VoidCallback? onTap;
  final IconData icon;
  @override
  Widget build(BuildContext context) {
    final title = record['tracking_number'] ?? record['booking_reference'] ?? record['order_number'] ?? record['invoice_number'] ?? record['receipt_number'] ?? record['container_number'] ?? record['name'] ?? record['title'] ?? subject;
    final status = record['status'] ?? record['delivery_status'] ?? record['goods_status'] ?? record['payment_status'];
    final container = record['container'] is Map ? record['container'] as Map : record;
    final route = record['route'] ?? (container['origin'] != null && container['destination'] != null ? '${container['origin']} → ${container['destination']}' : null);
    final detail = route ?? record['description'] ?? record['order_description'] ?? record['supplier_name'] ?? (record['created_at'] == null ? null : logisticsDate(record['created_at']));
    return Material(
      color: Colors.white,
      child: InkWell(
        onTap: onTap ?? () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => LogisticsRecordDetail(record: record, title: subject))),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(padding: const EdgeInsets.all(10), decoration: BoxDecoration(color: appCanvas, borderRadius: BorderRadius.circular(12)), child: Icon(icon, size: 22, color: brandNavy)),
            const SizedBox(width: 14),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('$title', style: const TextStyle(color: appInk, fontWeight: FontWeight.w800), maxLines: 2, overflow: TextOverflow.ellipsis),
              if (detail != null) ...[const SizedBox(height: 4), Text('$detail', maxLines: 2, overflow: TextOverflow.ellipsis)],
              if (status != null) ...[const SizedBox(height: 8), SahajomyStatusPill(label: '$status')],
            ])),
            const SizedBox(width: 8),
            const Icon(Icons.chevron_right_rounded, color: appMuted, size: 20),
          ]),
        ),
      ),
    );
  }
}

class LogisticsRecordDetail extends StatelessWidget {
  const LogisticsRecordDetail({required this.record, required this.title, super.key});
  final Map<String, dynamic> record;
  final String title;
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: SahajomyScreenHeader(title: title),
    body: ListView(padding: const EdgeInsets.all(24), children: [
      LogisticsIntro(title: title, description: 'Shipment, cargo and account details supplied by your service provider.'),
      SahajomyKeyValueList(entries: logisticsDetails(record)),
      for (final key in const ['container', 'shipping_label', 'warehouse', 'cargo_admin', 'supplier', 'totals'])
        if (record[key] is Map) ...[
          const SizedBox(height: 24),
          Text(sahajomyTitleCase(key), style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          SahajomyKeyValueList(entries: logisticsDetails(Map<String, dynamic>.from(record[key] as Map))),
        ],
    ]),
  );
}
