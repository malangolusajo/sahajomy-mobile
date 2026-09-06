import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import '../../../core/auth/session.dart';
import '../../../core/providers.dart';
import '../../../core/ui/sahajomy_ui.dart';

class SplashPage extends ConsumerStatefulWidget {
  const SplashPage({super.key});

  @override
  ConsumerState<SplashPage> createState() => _SplashPageState();
}

class _SplashPageState extends ConsumerState<SplashPage>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 850),
    )..forward();
    unawaited(_continueToApp());
  }

  Future<void> _continueToApp() async {
    final results = await Future.wait<Object?>([
      ref.read(sessionStoreProvider).read(),
      ref.read(tokenStorageProvider).getOnboardingCompleted(),
      Future<void>.delayed(const Duration(milliseconds: 1250)),
    ]);
    if (!mounted) return;
    final session = results[0] as Session?;
    final onboardingCompleted = results[1] as bool;
    context.go(
      session != null
          ? _homeFor(session.role)
          : onboardingCompleted
          ? '/sign-in'
          : '/onboarding',
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final scale = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeOutBack,
    );
    final fade = CurvedAnimation(
      parent: _controller,
      curve: const Interval(0, .72, curve: Curves.easeOut),
    );
    return Scaffold(
      backgroundColor: brandNavyDark,
      body: Semantics(
        label: 'Sahajomy is starting',
        child: Stack(
          fit: StackFit.expand,
          children: [
            const _SplashBackground(),
            SafeArea(
              child: Column(
                children: [
                  const Spacer(flex: 4),
                  ScaleTransition(
                    scale: scale,
                    child: const SahajomyBrandMark(
                      size: 104,
                      showShadow: false,
                    ),
                  ),
                  const SizedBox(height: 24),
                  FadeTransition(
                    opacity: fade,
                    child: const Column(
                      children: [
                        Text(
                          'SAHAJOMY',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 24,
                            fontWeight: FontWeight.w900,
                            letterSpacing: 4,
                          ),
                        ),
                        SizedBox(height: 10),
                        Text(
                          'Shipping made clear.',
                          style: TextStyle(
                            color: Color(0xFFB9CBD7),
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            letterSpacing: .4,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const Spacer(flex: 5),
                  FadeTransition(
                    opacity: fade,
                    child: const Padding(
                      padding: EdgeInsets.only(bottom: 34),
                      child: SizedBox(
                        width: 22,
                        height: 22,
                        child: CircularProgressIndicator(
                          strokeWidth: 2.2,
                          color: brandCoral,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SplashBackground extends StatelessWidget {
  const _SplashBackground();

  @override
  Widget build(BuildContext context) =>
      CustomPaint(painter: _SplashBackgroundPainter());
}

class _SplashBackgroundPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final glow = Paint()
      ..shader =
          RadialGradient(
            colors: [brandCoral.withValues(alpha: .13), Colors.transparent],
          ).createShader(
            Rect.fromCircle(
              center: Offset(size.width * .84, size.height * .16),
              radius: size.width * .64,
            ),
          );
    canvas.drawRect(Offset.zero & size, glow);

    final route = Paint()
      ..color = Colors.white.withValues(alpha: .045)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2;
    final path = Path()
      ..moveTo(-20, size.height * .74)
      ..cubicTo(
        size.width * .28,
        size.height * .58,
        size.width * .68,
        size.height * .92,
        size.width + 30,
        size.height * .67,
      );
    canvas.drawPath(path, route);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

String _homeFor(UserRole role) => switch (role) {
  UserRole.customer => '/customer',
  UserRole.cargoAdmin => '/cargo-admin',
  UserRole.sourcingAgent => '/sourcing-agent',
  UserRole.superAdmin => '/super-admin',
};
