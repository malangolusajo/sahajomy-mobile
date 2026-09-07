import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/auth/session.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/providers.dart';
import '../../../core/ui/sahajomy_ui.dart';
import '../../auth/data/auth_repository.dart';

class SplashPage extends ConsumerStatefulWidget {
  const SplashPage({super.key});

  @override
  ConsumerState<SplashPage> createState() => _SplashPageState();
}

class _SplashPageState extends ConsumerState<SplashPage>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  bool _checking = true;
  String? _error;

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
    setState(() {
      _checking = true;
      _error = null;
    });
    final sessionStore = ref.read(sessionStoreProvider);
    try {
      final results = await Future.wait<Object?>([
        sessionStore.read(),
        ref.read(tokenStorageProvider).getOnboardingCompleted(),
        Future<void>.delayed(const Duration(milliseconds: 1250)),
      ]);
      if (!mounted) return;
      final session = results[0] as Session?;
      final onboardingCompleted = results[1] as bool;
      if (session == null) {
        context.go(onboardingCompleted ? '/sign-in' : '/onboarding');
        return;
      }
      await ref.read(workspaceProvider.notifier).ready;
      final verified = await ref
          .read(authRepositoryProvider)
          .verifyStoredSession(session);
      await sessionStore.save(verified);
      if (mounted) context.go('/checking-workspace');
    } on ApiException catch (error) {
      if (error.isUnauthorized || error.isForbidden) {
        await ref.read(workspaceProvider.notifier).clearWorkspace();
        await sessionStore.clear();
        if (mounted) {
          context.go(
            error.message.toLowerCase().contains('suspended')
                ? '/account-suspended'
                : '/sign-in',
          );
        }
        return;
      }
      if (mounted) {
        setState(() {
          _checking = false;
          _error = 'We could not securely verify your session.';
        });
      }
    } on FormatException {
      await ref.read(workspaceProvider.notifier).clearWorkspace();
      await sessionStore.clear();
      if (mounted) context.go('/sign-in');
    } catch (_) {
      if (mounted) {
        setState(() {
          _checking = false;
          _error = 'Check your connection, then try again.';
        });
      }
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: const Color(0xFF060707),
    body: SafeArea(
      child: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 28),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const SahajomyBrandMark(size: 104, showShadow: false),
                const SizedBox(height: 64),
                const Text(
                  'Ship, source, and track goods\nfrom China to Africa.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: Color(0xFFCBD5DF),
                    fontSize: 13,
                    height: 1.4,
                  ),
                ),
                const SizedBox(height: 22),
                if (_checking)
                  const SizedBox(
                    width: 42,
                    child: LinearProgressIndicator(
                      color: Color(0xFFEFBF04),
                      backgroundColor: Color(0xFF282711),
                      minHeight: 4,
                      borderRadius: BorderRadius.all(Radius.circular(4)),
                      semanticsLabel: 'Starting app',
                    ),
                  ),
                if (_error != null) ...[
                  Text(
                    _error!,
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: Colors.white),
                  ),
                  TextButton(
                    onPressed: _checking ? null : _continueToApp,
                    child: const Text('Try again securely'),
                  ),
                ],
                const SizedBox(height: 32),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}
