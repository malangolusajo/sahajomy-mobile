import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../app/theme.dart';
import '../../../customer/presentation/customer_components.dart';
import '../../../repository_providers.dart';

/// Screen 115 — Financials overview
class AgentFinancialsPage extends ConsumerStatefulWidget {
  const AgentFinancialsPage({super.key});

  @override
  ConsumerState<AgentFinancialsPage> createState() => _AgentFinancialsPageState();
}

class _AgentFinancialsPageState extends ConsumerState<AgentFinancialsPage> {
  late Future<Map<String, dynamic>> _financials;

  @override
  void initState() {
    super.initState();
    _financials = ref.read(sourcingAgentBatchesRepositoryProvider).getFinancials();
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'FINANCIALS',
    title: 'Financial overview',
    notificationRoute: '/reference/agent-notifications',
    body: FutureBuilder<Map<String, dynamic>>(
      future: _financials,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return CustomerEmptyState(icon: Icons.error_outline, message: 'Could not load financials.', actionLabel: 'Retry', onAction: () => setState(() => _financials = ref.read(sourcingAgentBatchesRepositoryProvider).getFinancials()));
        }
        final d = snapshot.data ?? {};
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          children: [
            CustomerHeroCard(
              eyebrow: 'All batches',
              title: 'Total batch value',
              subtitle: '${d['currency'] ?? 'TZS'} ${_fmt(d['total_batch_value'])}',
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(child: _statCard('Orders', '${d['total_orders'] ?? 0}', Icons.shopping_bag_outlined, brandNavy)),
                const SizedBox(width: 12),
                Expanded(child: _statCard('Paid', '${d['paid_orders'] ?? 0}', Icons.check_circle_outline, appSuccess)),
                const SizedBox(width: 12),
                Expanded(child: _statCard('Unpaid', '${d['unpaid_orders'] ?? 0}', Icons.pending_outlined, appError)),
              ],
            ),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: appBorder)),
              child: Column(
                children: [
                  _row('Total batch value', '${d['currency'] ?? ''} ${_fmt(d['total_batch_value'])}'),
                  _row('Commission rate', '${d['commission_rate'] ?? '—'}%'),
                  _row('Total collected', '${d['currency'] ?? ''} ${_fmt(d['total_collected'])}'),
                  _row('Outstanding', '${d['currency'] ?? ''} ${_fmt(d['outstanding'])}', highlight: true),
                ],
              ),
            ),
          ],
        );
      },
    ),
  );

  String _fmt(dynamic v) {
    if (v == null) return '0';
    if (v is num) return v.toStringAsFixed(0);
    return '$v';
  }

  Widget _statCard(String label, String value, IconData icon, Color color) => Container(
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: appBorder)),
    child: Column(
      children: [
        Icon(icon, color: color, size: 24),
        const SizedBox(height: 4),
        Text(value, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 18)),
        Text(label, style: const TextStyle(color: appMuted, fontSize: 11)),
      ],
    ),
  );

  Widget _row(String label, String value, {bool highlight = false}) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 8),
    child: Row(children: [
      Expanded(child: Text(label, style: const TextStyle(color: appMuted))),
      Text(value, style: TextStyle(fontWeight: FontWeight.w800, color: highlight ? brandCoral : appInk)),
    ]),
  );
}

/// Screen 118 — Account
class AgentAccountPage extends StatelessWidget {
  const AgentAccountPage({super.key});

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'ACCOUNT',
    title: 'My account',
    notificationRoute: '/reference/agent-notifications',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        const CustomerHeroCard(eyebrow: 'Sourcing agent', title: 'Agent account', subtitle: 'Manage your profile, verification and preferences.'),
        const SizedBox(height: 16),
        _menuTile(context, Icons.person_outline, 'Profile', 'Edit your agent profile'),
        _menuTile(context, Icons.verified_outlined, 'Verification status', 'KYC and approval'),
        _menuTile(context, Icons.account_balance_wallet_outlined, 'Payout settings', 'Bank and mobile money'),
        _menuTile(context, Icons.notifications_none_rounded, 'Notifications', 'Alert preferences'),
        _menuTile(context, Icons.help_outline, 'Help & support', 'FAQs and contact'),
        const SizedBox(height: 24),
        OutlinedButton.icon(onPressed: () {}, icon: const Icon(Icons.logout_rounded), label: const Text('Sign out')),
      ],
    ),
  );

  Widget _menuTile(BuildContext context, IconData icon, String title, String subtitle) => Container(
    margin: const EdgeInsets.only(bottom: 10),
    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: appBorder)),
    child: ListTile(
      leading: Icon(icon, color: brandNavy),
      title: Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
      subtitle: Text(subtitle, style: const TextStyle(color: appMuted, fontSize: 12)),
      trailing: const Icon(Icons.chevron_right_rounded, color: appMuted),
      onTap: () {},
    ),
  );
}

/// Screen 119 — Verification status
class AgentVerificationPage extends StatelessWidget {
  const AgentVerificationPage({super.key});

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'VERIFICATION',
    title: 'Verification status',
    notificationRoute: '/reference/agent-notifications',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(color: appSuccess.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(16), border: Border.all(color: appSuccess)),
          child: Row(
            children: [
              const Icon(Icons.verified_rounded, color: appSuccess, size: 36),
              const SizedBox(width: 14),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: const [
                Text('Verified agent', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16, color: appSuccess)),
                Text('Your account is approved and fully operational.', style: TextStyle(color: appMuted, fontSize: 13)),
              ])),
            ],
          ),
        ),
        const SizedBox(height: 20),
        _step('Identity check', 'Completed', true),
        _step('Business registration', 'Completed', true),
        _step('Bank verification', 'Completed', true),
        _step('Phone verification', 'Completed', true),
      ],
    ),
  );

  Widget _step(String title, String status, bool done) => Container(
    margin: const EdgeInsets.only(bottom: 10),
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: appBorder)),
    child: Row(children: [
      Icon(done ? Icons.check_circle : Icons.radio_button_unchecked, color: done ? appSuccess : appMuted),
      const SizedBox(width: 12),
      Expanded(child: Text(title, style: const TextStyle(fontWeight: FontWeight.w700))),
      Text(status, style: TextStyle(color: done ? appSuccess : appMuted, fontWeight: FontWeight.w600)),
    ]),
  );
}

/// Screen 177 — Instagram import
class AgentInstagramImportPage extends ConsumerStatefulWidget {
  const AgentInstagramImportPage({required this.batchId, super.key});
  final String batchId;

  @override
  ConsumerState<AgentInstagramImportPage> createState() => _AgentInstagramImportPageState();
}

class _AgentInstagramImportPageState extends ConsumerState<AgentInstagramImportPage> {
  final _url = TextEditingController();
  String? _imageUrl;
  bool _busy = false;

  @override
  void dispose() {
    _url.dispose();
    super.dispose();
  }

  Future<void> _import() async {
    if (_url.text.trim().isEmpty) return;
    setState(() => _busy = true);
    try {
      final res = await ref.read(sourcingAgentBatchesRepositoryProvider).importInstagramImage(
        batchId: widget.batchId,
        instagramUrl: _url.text.trim(),
      );
      setState(() => _imageUrl = res['image_url'] as String?);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    eyebrow: 'IMPORT',
    title: 'Import from Instagram',
    notificationRoute: '/reference/agent-notifications',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        const CustomerHeroCard(eyebrow: 'Instagram', title: 'Import product image', subtitle: 'Paste an Instagram post link to fetch the product photo.'),
        const SizedBox(height: 16),
        TextFormField(
          controller: _url,
          decoration: const InputDecoration(labelText: 'Instagram post URL', hintText: 'https://instagram.com/p/...'),
          keyboardType: TextInputType.url,
        ),
        const SizedBox(height: 16),
        FilledButton.icon(onPressed: _busy ? null : _import, icon: const Icon(Icons.download_rounded), label: Text(_busy ? 'Importing...' : 'Import image')),
        if (_imageUrl != null) ...[
          const SizedBox(height: 20),
          const Text('Imported image', style: TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: Image.network(
              _imageUrl!,
              height: 240,
              width: double.infinity,
              fit: BoxFit.cover,
              errorBuilder: (_, _, _) => Container(height: 240, color: appCanvas, child: const Icon(Icons.broken_image_outlined, size: 48, color: appMuted)),
            ),
          ),
          const SizedBox(height: 12),
          SelectableText(_imageUrl!, style: const TextStyle(fontSize: 12, fontFamily: 'monospace', color: appMuted)),
        ],
      ],
    ),
  );
}
