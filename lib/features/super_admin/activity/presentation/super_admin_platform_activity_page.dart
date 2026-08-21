import 'package:flutter/material.dart';

import '../../../../core/ui/sahajomy_ui.dart';
import '../../dashboard/data/super_admin_dashboard_repository.dart';
import '../../users/data/super_admin_users_repository.dart';

class SuperAdminPlatformActivityPage extends StatefulWidget {
  const SuperAdminPlatformActivityPage({super.key});

  @override
  State<SuperAdminPlatformActivityPage> createState() =>
      _SuperAdminPlatformActivityPageState();
}

class _SuperAdminPlatformActivityPageState
    extends State<SuperAdminPlatformActivityPage> {
  final _dashboardRepository = SuperAdminDashboardRepository();
  final _usersRepository = SuperAdminUsersRepository();
  late Future<List<Map<String, dynamic>>> _data = _load();

  Future<List<Map<String, dynamic>>> _load() => Future.wait([
    _dashboardRepository.loadOverview(),
    _usersRepository.listUsers(),
  ]);

  void _retry() => setState(() => _data = _load());

  @override
  Widget build(
    BuildContext context,
  ) => FutureBuilder<List<Map<String, dynamic>>>(
    future: _data,
    builder: (context, snapshot) {
      if (snapshot.connectionState != ConnectionState.done) {
        return const Center(child: CircularProgressIndicator());
      }
      if (snapshot.hasError) {
        return SahajomyMessageState(
          icon: Icons.wifi_off_rounded,
          message: 'Platform activity is unavailable right now.',
          actionLabel: 'Try again',
          onAction: _retry,
        );
      }

      final overview = snapshot.data![0];
      final users = (snapshot.data![1]['data'] as List? ?? const [])
          .cast<Map<String, dynamic>>();
      final activity = <_ActivityItem>[
        _ActivityItem(
          icon: Icons.verified_user_outlined,
          title: '${overview['pending_approvals'] ?? 0} pending approvals',
          subtitle: 'Review the governance queue across platform roles.',
          timeLabel: 'Live',
        ),
        _ActivityItem(
          icon: Icons.percent_rounded,
          title: 'Commission rate ${overview['current_commission_rate'] ?? 0}%',
          subtitle: 'Current platform configuration is active.',
          timeLabel: 'Today',
        ),
        for (final user in users.take(4))
          _ActivityItem(
            icon: '${user['is_verified']}' == 'true'
                ? Icons.check_circle_outline_rounded
                : Icons.hourglass_bottom_rounded,
            title: user['name'] as String? ?? 'User',
            subtitle:
                '${user['role'] ?? 'Role'} • ${user['status'] ?? 'Status'}',
            timeLabel: user['is_verified'] == true ? 'Approved' : 'Pending',
          ),
      ];

      return ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            'Platform activity',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 6),
          const Text(
            'An auditable record of platform changes and governance signals.',
          ),
          const SizedBox(height: 20),
          Container(
            decoration: const BoxDecoration(
              color: Colors.white,
              border: Border.symmetric(
                vertical: BorderSide(color: Color(0xFFE2E8F0)),
              ),
            ),
            child: Column(
              children: [for (final item in activity) _ActivityRow(item: item)],
            ),
          ),
          const SizedBox(height: 20),
          OutlinedButton(
            onPressed: () => ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text(
                  'Audit export will be available with the server export route.',
                ),
              ),
            ),
            child: const Text('Export audit log'),
          ),
        ],
      );
    },
  );
}

class _ActivityItem {
  const _ActivityItem({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.timeLabel,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final String timeLabel;
}

class _ActivityRow extends StatelessWidget {
  const _ActivityRow({required this.item});

  final _ActivityItem item;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(vertical: 14),
    decoration: const BoxDecoration(
      border: Border(bottom: BorderSide(color: Color(0xFFE2E8F0))),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(width: 12),
        CircleAvatar(
          radius: 16,
          backgroundColor: const Color(0xFFFFEEE9),
          child: Icon(item.icon, size: 16, color: const Color(0xFFE85A3A)),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                item.title,
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                item.subtitle,
                style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
              ),
            ],
          ),
        ),
        const SizedBox(width: 8),
        Text(
          item.timeLabel,
          style: const TextStyle(fontSize: 10, color: Color(0xFF94A3B8)),
        ),
        const SizedBox(width: 12),
      ],
    ),
  );
}
