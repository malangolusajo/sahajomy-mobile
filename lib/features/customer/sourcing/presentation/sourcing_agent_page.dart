import 'package:flutter/material.dart';

import '../../../../app/theme.dart';
import '../../presentation/customer_components.dart';

class SourcingAgentPage extends StatelessWidget {
  const SourcingAgentPage({required this.agent, super.key});

  final Map<String, dynamic> agent;

  @override
  Widget build(BuildContext context) {
    final name = agent['name'] ?? agent['company_name'] ?? 'Sourcing agent';
    final country = agent['country'] ?? 'China';
    final verified = agent['is_verified'] == true || agent['verification_status'] == 'verified';
    final productsCount = agent['products_count'] ?? 0;
    final openBatches = agent['open_batches'] ?? 0;
    return CustomerScaffold(
      title: 'Sourcing agent',
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          CustomerHeroCard(
            eyebrow: 'Sourcing agent',
            title: '$name',
            subtitle: 'Registered sourcing agent · $country',
          ),
          const SizedBox(height: 24),
          Container(
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: appBorder),
            ),
            child: Column(
              children: [
                _agentRow('VR', 'Verification', verified ? 'Profile verified' : 'Not verified',
                    verified ? 'Verified' : null, brandCoral),
                const Divider(height: 1, indent: 60),
                _agentRow('PR', 'Products', '$productsCount published products', null, appMuted),
                const Divider(height: 1, indent: 60),
                _agentRow('BT', 'Open batches', '$openBatches batches accepting orders', null, appMuted),
              ],
            ),
          ),
          const SizedBox(height: 20),
          FilledButton(
            onPressed: () => Navigator.of(context).maybePop(),
            child: const Text('Browse products'),
          ),
        ],
      ),
    );
  }

  Widget _agentRow(String badge, String title, String subtitle, String? tag, Color badgeColor) =>
      Padding(
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
            if (tag != null)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: appSuccess.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(tag, style: const TextStyle(color: appSuccess, fontSize: 12, fontWeight: FontWeight.w700)),
              ),
          ],
        ),
      );
}
