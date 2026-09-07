import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/notifications/notification_permission.dart';
import '../../../core/ui/core_flow_ui.dart';

class StayUpdatedPage extends ConsumerStatefulWidget {
  const StayUpdatedPage({super.key});
  @override
  ConsumerState<StayUpdatedPage> createState() => _StayUpdatedPageState();
}

class _StayUpdatedPageState extends ConsumerState<StayUpdatedPage> {
  bool _busy = false;
  String? _status;
  Future<void> _request() async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final status = await ref.read(notificationPermissionProvider).request();
      if (mounted) setState(() => _status = status);
    } catch (_) {
      if (mounted) setState(() => _status = 'error');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _settings() async {
    try {
      await ref.read(notificationPermissionProvider).openSettings();
    } catch (_) {
      if (mounted) setState(() => _status = 'error');
    }
  }

  @override
  Widget build(BuildContext context) => CoreFlowPage(
    title: 'Stay updated',
    onBack: () => context.go('/account/workspaces'),
    children: [
      const CoreHero(
        eyebrow: 'NOTIFICATIONS',
        title: 'Stay updated',
        description: 'Get important booking, warehouse, payment and shipment notifications without repeatedly checking the app.',
      ),
      const SizedBox(height: 16),
      const CoreGroup(
        children: [
          CoreChoice(
            title: 'Booking updates',
            subtitle: 'Confirmation and service changes',
            icon: Icons.bookmark_border,
          ),
          CoreChoice(
            title: 'Warehouse updates',
            subtitle: 'Goods received and handling status',
            icon: Icons.warehouse_outlined,
          ),
          CoreChoice(
            title: 'Tracking alerts',
            subtitle: 'Departure, transit and arrival updates',
            icon: Icons.local_shipping_outlined,
          ),
        ],
      ),
      const SizedBox(height: 12),
      if (_status != null)
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Text(switch (_status) {
            'granted' => 'Notification permission is allowed on this device.',
            'denied' => 'Notifications are disabled. You can allow them in device settings, or continue and check updates in the app.',
            'unavailable' => 'Device notifications are unavailable here. You can still check updates in the app.',
            _ => 'Unable to request notification permission. Try again or continue.',
          }, style: const TextStyle(color: coreMuted, fontSize: 13)),
        ),
      FilledButton(
        onPressed: _busy
            ? null
            : _status == 'granted' || _status == 'unavailable'
            ? () => context.go('/account/workspaces')
            : _request,
        child: Text(
          _busy
              ? 'Requesting permission…'
              : _status == 'granted' || _status == 'unavailable'
              ? 'Continue'
              : 'Allow notifications',
        ),
      ),
      if (_status == 'denied')
        TextButton(
          onPressed: _busy ? null : _settings,
          child: const Text('Open device settings'),
        ),
      TextButton(
        onPressed: _busy ? null : () => context.go('/account/workspaces'),
        child: const Text('Not now'),
      ),
    ],
  );
}
