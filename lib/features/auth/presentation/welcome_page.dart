import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import '../../../core/ui/sahajomy_ui.dart';

class WelcomePage extends StatelessWidget {
  const WelcomePage({super.key});

  @override
  Widget build(BuildContext context) => Scaffold(
    body: Stack(
      children: [
        Positioned(
          top: -90,
          right: -80,
          child: Container(
            width: 260,
            height: 260,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: brandCoral.withValues(alpha: .07),
            ),
          ),
        ),
        SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(24, 34, 24, 24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SahajomyWordmark(markSize: 42),
                const Spacer(flex: 3),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 7,
                  ),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFE9E3),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: const Text(
                    'SHIPPING • SOURCING • TRACKING',
                    style: TextStyle(
                      color: brandCoral,
                      fontSize: 10,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 1,
                    ),
                  ),
                ),
                const SizedBox(height: 20),
                Text(
                  'Ship smarter.\nGrow further.',
                  style: Theme.of(context).textTheme.displaySmall,
                ),
                const SizedBox(height: 18),
                const Text(
                  'Book cargo, follow every milestone, and manage your logistics from one secure workspace.',
                  style: TextStyle(fontSize: 17, height: 1.6),
                ),
                const SizedBox(height: 30),
                const _TrustPoint(
                  icon: Icons.verified_user_outlined,
                  text: 'Secure role-based access',
                ),
                const SizedBox(height: 13),
                const _TrustPoint(
                  icon: Icons.route_outlined,
                  text: 'Clear shipment visibility',
                ),
                const Spacer(flex: 4),
                FilledButton(
                  onPressed: () => context.go('/onboarding'),
                  child: const Text('Get started'),
                ),
                const SizedBox(height: 6),
                Center(
                  child: TextButton(
                    onPressed: () => context.go('/sign-in'),
                    child: const Text('I already have an account'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    ),
  );
}

class _TrustPoint extends StatelessWidget {
  const _TrustPoint({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Row(
    children: [
      Container(
        width: 38,
        height: 38,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: appBorder),
        ),
        child: Icon(icon, size: 20, color: brandTeal),
      ),
      const SizedBox(width: 12),
      Text(
        text,
        style: const TextStyle(
          color: appInk,
          fontSize: 14,
          fontWeight: FontWeight.w700,
        ),
      ),
    ],
  );
}
