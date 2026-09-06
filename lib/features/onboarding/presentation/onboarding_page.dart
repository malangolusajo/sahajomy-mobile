import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:go_router/go_router.dart';
import 'package:smooth_page_indicator/smooth_page_indicator.dart';

import '../../../app/theme.dart';
import '../../../core/providers.dart';
import '../../../core/ui/sahajomy_ui.dart';

class OnboardingPage extends ConsumerStatefulWidget {
  const OnboardingPage({super.key});

  @override
  ConsumerState<OnboardingPage> createState() => _OnboardingPageState();
}

class _OnboardingPageState extends ConsumerState<OnboardingPage> {
  final _pageController = PageController();
  var _currentPage = 0;
  var _isCompleting = false;

  static const _pages = [
    _OnboardingData(
      illustration: 'assets/onboarding/illustration_1.svg',
      eyebrow: 'BOOK WITH CLARITY',
      title: 'Move cargo with confidence',
      description: 'Compare sea and air services, prepare your shipping details, and confirm each booking with a clear review step.',
      benefit: 'Clear options. Fewer surprises.',
      icon: Icons.local_shipping_outlined,
    ),
    _OnboardingData(
      illustration: 'assets/onboarding/illustration_2.svg',
      eyebrow: 'STAY INFORMED',
      title: 'Know where every shipment stands',
      description: 'Follow milestones, documents, and warehouse updates from one secure place—without chasing status messages.',
      benefit: 'The right update, right when you need it.',
      icon: Icons.route_outlined,
    ),
    _OnboardingData(
      illustration: 'assets/onboarding/illustration_3.svg',
      eyebrow: 'WORK YOUR WAY',
      title: 'One app for every workspace',
      description: 'Use your personal, sourcing, or cargo operations workspace while Sahajomy keeps each company context separate.',
      benefit: 'Secure access built around your role.',
      icon: Icons.domain_outlined,
    ),
  ];

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  Future<void> _complete() async {
    if (_isCompleting) return;
    setState(() => _isCompleting = true);
    await ref.read(tokenStorageProvider).setOnboardingCompleted();
    ref.invalidate(onboardingCompletedProvider);
    if (mounted) context.go('/sign-in');
  }

  void _next() {
    if (_currentPage == _pages.length - 1) {
      _complete();
      return;
    }
    _pageController.nextPage(
      duration: const Duration(milliseconds: 420),
      curve: Curves.easeOutCubic,
    );
  }

  @override
  Widget build(BuildContext context) {
    final isLast = _currentPage == _pages.length - 1;
    return Scaffold(
      backgroundColor: appCanvas,
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 12, 12, 4),
              child: Row(
                children: [
                  const SahajomyWordmark(markSize: 36),
                  const Spacer(),
                  AnimatedOpacity(
                    opacity: isLast ? 0 : 1,
                    duration: const Duration(milliseconds: 180),
                    child: IgnorePointer(
                      ignoring: isLast,
                      child: TextButton(
                        onPressed: _complete,
                        child: const Text('Skip'),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: PageView.builder(
                controller: _pageController,
                itemCount: _pages.length,
                onPageChanged: (page) => setState(() => _currentPage = page),
                itemBuilder: (context, index) => _OnboardingSlide(
                  data: _pages[index],
                  pageNumber: index + 1,
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 14, 24, 24),
              child: Column(
                children: [
                  SmoothPageIndicator(
                    controller: _pageController,
                    count: _pages.length,
                    effect: const ExpandingDotsEffect(
                      activeDotColor: brandCoral,
                      dotColor: appBorder,
                      dotHeight: 7,
                      dotWidth: 7,
                      expansionFactor: 3.2,
                      spacing: 7,
                    ),
                  ),
                  const SizedBox(height: 22),
                  FilledButton.icon(
                    onPressed: _isCompleting ? null : _next,
                    icon: _isCompleting
                        ? const SizedBox.square(
                            dimension: 18,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          )
                        : Icon(
                            isLast
                                ? Icons.arrow_forward_rounded
                                : Icons.chevron_right_rounded,
                          ),
                    label: Text(isLast ? 'Continue to sign in' : 'Continue'),
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

class _OnboardingData {
  const _OnboardingData({
    required this.illustration,
    required this.eyebrow,
    required this.title,
    required this.description,
    required this.benefit,
    required this.icon,
  });

  final String illustration;
  final String eyebrow;
  final String title;
  final String description;
  final String benefit;
  final IconData icon;
}

class _OnboardingSlide extends StatelessWidget {
  const _OnboardingSlide({required this.data, required this.pageNumber});

  final _OnboardingData data;
  final int pageNumber;

  @override
  Widget build(BuildContext context) => SingleChildScrollView(
    padding: const EdgeInsets.fromLTRB(24, 12, 24, 8),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          height: 276,
          width: double.infinity,
          clipBehavior: Clip.antiAlias,
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [Color(0xFF164F73), brandNavyDark],
            ),
            borderRadius: BorderRadius.circular(30),
            boxShadow: [
              BoxShadow(
                color: brandNavy.withValues(alpha: .16),
                blurRadius: 30,
                offset: const Offset(0, 14),
              ),
            ],
          ),
          child: Stack(
            children: [
              const Positioned(
                right: -50,
                top: -55,
                child: _DecorativeCircle(size: 180, opacity: .06),
              ),
              const Positioned(
                left: -36,
                bottom: -72,
                child: _DecorativeCircle(size: 170, opacity: .045),
              ),
              Positioned(
                left: 18,
                top: 18,
                child: Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: .12),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: Colors.white.withValues(alpha: .16),
                    ),
                  ),
                  child: Icon(data.icon, color: Colors.white, size: 22),
                ),
              ),
              Positioned(
                right: 20,
                top: 22,
                child: Text(
                  '0$pageNumber',
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: .45),
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1.2,
                  ),
                ),
              ),
              Positioned.fill(
                top: 56,
                child: Padding(
                  padding: const EdgeInsets.all(22),
                  child: SvgPicture.asset(
                    data.illustration,
                    fit: BoxFit.contain,
                    semanticsLabel: data.title,
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 34),
        Text(
          data.eyebrow,
          style: const TextStyle(
            color: brandCoral,
            fontSize: 11,
            fontWeight: FontWeight.w900,
            letterSpacing: 1.45,
          ),
        ),
        const SizedBox(height: 10),
        Text(data.title, style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 13),
        Text(data.description, style: Theme.of(context).textTheme.bodyLarge),
        const SizedBox(height: 20),
        Row(
          children: [
            Container(
              width: 30,
              height: 30,
              decoration: BoxDecoration(
                color: const Color(0xFFE5F5F2),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Icon(
                Icons.check_rounded,
                color: brandTeal,
                size: 18,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                data.benefit,
                style: const TextStyle(
                  color: appInk,
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
      ],
    ),
  );
}

class _DecorativeCircle extends StatelessWidget {
  const _DecorativeCircle({required this.size, required this.opacity});

  final double size;
  final double opacity;

  @override
  Widget build(BuildContext context) => Container(
    width: size,
    height: size,
    decoration: BoxDecoration(
      shape: BoxShape.circle,
      color: Colors.white.withValues(alpha: opacity),
    ),
  );
}
