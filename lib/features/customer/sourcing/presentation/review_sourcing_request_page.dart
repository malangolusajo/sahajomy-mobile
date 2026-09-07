import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../app/theme.dart';
import '../../../../features/repository_providers.dart';
import '../../presentation/customer_components.dart';

class ReviewSourcingRequestPage extends ConsumerStatefulWidget {
  const ReviewSourcingRequestPage({
    required this.product,
    required this.quantity,
    required this.color,
    required this.destination,
    required this.notes,
    super.key,
  });

  final Map<String, dynamic> product;
  final int quantity;
  final String color;
  final String destination;
  final String notes;

  @override
  ConsumerState<ReviewSourcingRequestPage> createState() => _ReviewSourcingRequestPageState();
}

class _ReviewSourcingRequestPageState extends ConsumerState<ReviewSourcingRequestPage> {
  bool _busy = false;

  Future<void> _submit() async {
    setState(() => _busy = true);
    try {
      await ref.read(publicServicesRepositoryProvider).placeMarketplaceOrder({
        'product_id': widget.product['id'],
        'quantity': widget.quantity,
        'preferred_color': widget.color,
        'destination': widget.destination,
        'notes': widget.notes,
      });
      if (mounted) {
        Navigator.of(context).pushReplacementNamed('/customer/sourcing-request-submitted');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not submit request: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Review sourcing request',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        Container(
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: appBorder),
          ),
          child: Column(
            children: [
              _row('PR', 'Product', widget.product['name'] ?? '—', brandCoral),
              const Divider(height: 1, indent: 60),
              _row('QT', 'Quantity', '${widget.quantity} pieces${widget.color.isNotEmpty ? ' · ${widget.color}' : ''}', appMuted),
              const Divider(height: 1, indent: 60),
              _row('AG', 'Sourcing agent', widget.product['agent_name'] ?? 'Sourcing agent', appMuted),
              const Divider(height: 1, indent: 60),
              _row('DS', 'Destination', widget.destination, appMuted),
            ],
          ),
        ),
        const SizedBox(height: 24),
        FilledButton(
          onPressed: _busy ? null : _submit,
          child: Text(_busy ? 'Submitting...' : 'Submit sourcing request'),
        ),
      ],
    ),
  );

  Widget _row(String badge, String title, String subtitle, Color badgeColor) => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    child: Row(
      children: [
        Container(
          width: 40,
          height: 40,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: badgeColor.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Text(badge, style: TextStyle(color: badgeColor, fontWeight: FontWeight.w800)),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
              const SizedBox(height: 2),
              Text(subtitle, style: const TextStyle(color: appMuted, fontSize: 13)),
            ],
          ),
        ),
      ],
    ),
  );
}
