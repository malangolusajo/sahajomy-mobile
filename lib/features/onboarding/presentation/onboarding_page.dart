import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:smooth_page_indicator/smooth_page_indicator.dart';

import '../../../app/theme.dart';
import '../../../core/providers.dart';

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
      scene: _OnboardingScene.source,
      eyebrow: 'SOURCE',
      title: 'Find it in China. We’ll help you bring it home.',
      description: 'Browse products, work with a sourcing agent, and keep your orders and China delivery details together.',
      services: [
        _ServiceItem(Icons.storefront_outlined, 'Agizisha marketplace'),
        _ServiceItem(Icons.support_agent_rounded, 'Sourcing support'),
        _ServiceItem(Icons.receipt_long_outlined, 'Order management'),
        _ServiceItem(Icons.location_on_outlined, 'China addresses'),
      ],
    ),
    _OnboardingData(
      scene: _OnboardingScene.ship,
      eyebrow: 'SHIP',
      title: 'Small parcel or full container—it’s your call.',
      description: 'Compare sea freight and Express Air Cargo, book the space you need, and see the details before you confirm.',
      services: [
        _ServiceItem(Icons.directions_boat_outlined, 'Sea freight'),
        _ServiceItem(Icons.flight_takeoff_rounded, 'Express Air Cargo'),
        _ServiceItem(Icons.inventory_2_outlined, 'Containers'),
        _ServiceItem(Icons.event_available_outlined, 'Space bookings'),
      ],
    ),
    _OnboardingData(
      scene: _OnboardingScene.follow,
      eyebrow: 'STAY UPDATED',
      title: 'Know what’s happening without chasing updates.',
      description: 'Follow shipment milestones, keep documents and packing lists close, and get the alerts that matter.',
      services: [
        _ServiceItem(Icons.local_shipping_outlined, 'Your shipments'),
        _ServiceItem(Icons.route_outlined, 'Shipment tracking'),
        _ServiceItem(Icons.description_outlined, 'Documents & packing lists'),
        _ServiceItem(Icons.notifications_none_rounded, 'Status alerts'),
      ],
    ),
    _OnboardingData(
      scene: _OnboardingScene.collect,
      eyebrow: 'COLLECT',
      title: 'Your parcels are ready. Pickup stays simple.',
      description: 'See what has reached the warehouse, request one or several parcels, and collect securely with a short-lived QR code or PIN.',
      services: [
        _ServiceItem(Icons.warehouse_outlined, 'Warehouse parcels'),
        _ServiceItem(Icons.checklist_rounded, 'Multi-parcel requests'),
        _ServiceItem(Icons.qr_code_2_rounded, 'Secure QR & PIN'),
        _ServiceItem(Icons.inventory_outlined, 'Collection status'),
      ],
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
      duration: const Duration(milliseconds: 360),
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
            SizedBox(
              height: 52,
              child: Align(
                alignment: Alignment.centerRight,
                child: Padding(
                  padding: const EdgeInsets.only(right: 16),
                  child: TextButton(
                    onPressed: _isCompleting ? null : _complete,
                    child: const Text('Skip'),
                  ),
                ),
              ),
            ),
            Expanded(
              child: PageView.builder(
                controller: _pageController,
                itemCount: _pages.length,
                onPageChanged: (page) => setState(() => _currentPage = page),
                itemBuilder: (context, index) =>
                    _OnboardingSlide(data: _pages[index]),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 12, 24, 24),
              child: Row(
                children: [
                  Semantics(
                    label: 'Page ${_currentPage + 1} of ${_pages.length}',
                    child: SmoothPageIndicator(
                      controller: _pageController,
                      count: _pages.length,
                      effect: const ExpandingDotsEffect(
                        activeDotColor: brandNavy,
                        dotColor: appBorder,
                        dotHeight: 7,
                        dotWidth: 7,
                        expansionFactor: 3.4,
                        spacing: 7,
                      ),
                    ),
                  ),
                  const Spacer(),
                  SizedBox(
                    width: isLast ? 220 : 136,
                    child: FilledButton(
                      onPressed: _isCompleting ? null : _next,
                      child: _isCompleting
                          ? const SizedBox.square(
                              dimension: 18,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: Colors.white,
                              ),
                            )
                          : isLast
                          ? const Text('Get started')
                          : const Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text('Next'),
                                SizedBox(width: 7),
                                Icon(Icons.arrow_forward_rounded, size: 18),
                              ],
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

enum _OnboardingScene { source, ship, follow, collect }

class _OnboardingData {
  const _OnboardingData({
    required this.scene,
    required this.eyebrow,
    required this.title,
    required this.description,
    required this.services,
  });

  final _OnboardingScene scene;
  final String eyebrow;
  final String title;
  final String description;
  final List<_ServiceItem> services;
}

class _ServiceItem {
  const _ServiceItem(this.icon, this.label);

  final IconData icon;
  final String label;
}

class _OnboardingSlide extends StatelessWidget {
  const _OnboardingSlide({required this.data});

  final _OnboardingData data;

  @override
  Widget build(BuildContext context) => SingleChildScrollView(
    padding: const EdgeInsets.fromLTRB(24, 4, 24, 8),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _EditorialScene(scene: data.scene),
        const SizedBox(height: 28),
        Text(
          data.eyebrow,
          style: const TextStyle(
            color: brandCoral,
            fontSize: 11,
            fontWeight: FontWeight.w900,
            letterSpacing: 1.35,
          ),
        ),
        const SizedBox(height: 9),
        Text(data.title, style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 11),
        Text(data.description, style: Theme.of(context).textTheme.bodyLarge),
        const SizedBox(height: 18),
        _ServiceGrid(services: data.services),
      ],
    ),
  );
}

class _ServiceGrid extends StatelessWidget {
  const _ServiceGrid({required this.services});

  final List<_ServiceItem> services;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final itemWidth = (constraints.maxWidth - 8) / 2;
      return Wrap(
        spacing: 8,
        runSpacing: 8,
        children: [
          for (final service in services)
            SizedBox(
              width: itemWidth,
              child: Semantics(
                label: service.label,
                child: Container(
                  constraints: const BoxConstraints(minHeight: 42),
                  padding: const EdgeInsets.symmetric(
                    horizontal: 11,
                    vertical: 9,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: appBorder),
                  ),
                  child: Row(
                    children: [
                      Icon(service.icon, size: 17, color: brandTeal),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          service.label,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: appInk,
                            fontSize: 12,
                            height: 1.25,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      );
    },
  );
}

class _EditorialScene extends StatelessWidget {
  const _EditorialScene({required this.scene});

  final _OnboardingScene scene;

  @override
  Widget build(BuildContext context) {
    final (background, child, label) = switch (scene) {
      _OnboardingScene.source => (
        const Color(0xFFFFF1EC),
        const _SourceScene(),
        'A shopper browsing products with help from a sourcing agent',
      ),
      _OnboardingScene.ship => (
        const Color(0xFFEAF3F7),
        const _ShippingScene(),
        'Sea freight and air cargo choices',
      ),
      _OnboardingScene.follow => (
        const Color(0xFFEAF6F3),
        const _TrackingScene(),
        'Shipment milestones and a useful status update',
      ),
      _OnboardingScene.collect => (
        const Color(0xFFFFF3E8),
        const _CollectionScene(),
        'Several ready parcels and a secure collection code',
      ),
    };

    return Semantics(
      image: true,
      label: label,
      child: ExcludeSemantics(
        child: Container(
          height: 238,
          width: double.infinity,
          clipBehavior: Clip.antiAlias,
          decoration: BoxDecoration(
            color: background,
            borderRadius: BorderRadius.circular(28),
          ),
          child: Stack(
            children: [
              Positioned(
                right: -36,
                top: -42,
                child: Container(
                  width: 128,
                  height: 128,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.white.withValues(alpha: .45),
                  ),
                ),
              ),
              Positioned.fill(
                child: MediaQuery.withNoTextScaling(child: child),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SourceScene extends StatelessWidget {
  const _SourceScene();

  @override
  Widget build(BuildContext context) => Stack(
    children: [
      Positioned(
        left: 34,
        top: 24,
        child: Transform.rotate(
          angle: -.035,
          child: Container(
            width: 188,
            height: 188,
            padding: const EdgeInsets.fromLTRB(14, 14, 14, 12),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(22),
              boxShadow: const [
                BoxShadow(
                  color: Color(0x190B3857),
                  blurRadius: 24,
                  offset: Offset(0, 12),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.search_rounded, size: 18, color: appMuted),
                    SizedBox(width: 7),
                    Expanded(
                      child: Text(
                        'Search products',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          color: appMuted,
                          fontSize: 10,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                const Expanded(
                  child: Row(
                    children: [
                      Expanded(
                        child: _ProductTile(
                          color: Color(0xFFE8F2F6),
                          icon: Icons.chair_outlined,
                          label: 'Home',
                        ),
                      ),
                      SizedBox(width: 8),
                      Expanded(
                        child: _ProductTile(
                          color: Color(0xFFFFE9E2),
                          icon: Icons.checkroom_outlined,
                          label: 'Fashion',
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 10),
                const Row(
                  children: [
                    Icon(Icons.verified_rounded, size: 14, color: brandTeal),
                    SizedBox(width: 5),
                    Expanded(
                      child: Text(
                        'Product details checked',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          color: appInk,
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
      Positioned(
        right: 24,
        bottom: 28,
        child: Container(
          width: 152,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: brandNavy,
            borderRadius: BorderRadius.circular(17),
            boxShadow: const [
              BoxShadow(
                color: Color(0x330B3857),
                blurRadius: 20,
                offset: Offset(0, 9),
              ),
            ],
          ),
          child: const Row(
            children: [
              _PersonAvatar(),
              SizedBox(width: 9),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'A real person can help',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 10,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    SizedBox(height: 3),
                    Text(
                      'Sourcing support',
                      style: TextStyle(color: Color(0xFFBFD6E3), fontSize: 9),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    ],
  );
}

class _ProductTile extends StatelessWidget {
  const _ProductTile({
    required this.color,
    required this.icon,
    required this.label,
  });

  final Color color;
  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(9),
    decoration: BoxDecoration(
      color: color,
      borderRadius: BorderRadius.circular(13),
    ),
    child: Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(icon, size: 31, color: brandNavy),
        const SizedBox(height: 7),
        Text(
          label,
          style: const TextStyle(
            color: appInk,
            fontSize: 10,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    ),
  );
}

class _PersonAvatar extends StatelessWidget {
  const _PersonAvatar();

  @override
  Widget build(BuildContext context) => Container(
    width: 36,
    height: 36,
    decoration: const BoxDecoration(
      color: Color(0xFFFFD8CC),
      shape: BoxShape.circle,
    ),
    child: const Icon(Icons.person_rounded, color: brandCoral, size: 23),
  );
}

class _ShippingScene extends StatelessWidget {
  const _ShippingScene();

  @override
  Widget build(BuildContext context) => Stack(
    children: [
      const Positioned(
        left: 22,
        right: 22,
        top: 29,
        child: Row(
          children: [
            _TransportChoice(
              icon: Icons.directions_boat_rounded,
              title: 'Sea freight',
              detail: 'More room',
              selected: true,
            ),
            SizedBox(width: 10),
            _TransportChoice(
              icon: Icons.flight_rounded,
              title: 'Air cargo',
              detail: 'Moves faster',
            ),
          ],
        ),
      ),
      Positioned(
        left: 34,
        right: 34,
        bottom: 27,
        child: Container(
          height: 86,
          padding: const EdgeInsets.symmetric(horizontal: 17, vertical: 14),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(19),
            boxShadow: const [
              BoxShadow(
                color: Color(0x160B3857),
                blurRadius: 22,
                offset: Offset(0, 10),
              ),
            ],
          ),
          child: Row(
            children: [
              Container(
                width: 54,
                height: 54,
                decoration: BoxDecoration(
                  color: const Color(0xFFFFEAE4),
                  borderRadius: BorderRadius.circular(15),
                ),
                child: const Icon(
                  Icons.inventory_2_rounded,
                  color: brandCoral,
                  size: 27,
                ),
              ),
              const SizedBox(width: 13),
              const Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Your cargo, your choice',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: appInk,
                        fontSize: 13,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    SizedBox(height: 5),
                    Text(
                      'Compare before you book',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(color: appMuted, fontSize: 10),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.arrow_forward_rounded, color: brandNavy),
            ],
          ),
        ),
      ),
    ],
  );
}

class _TransportChoice extends StatelessWidget {
  const _TransportChoice({
    required this.icon,
    required this.title,
    required this.detail,
    this.selected = false,
  });

  final IconData icon;
  final String title;
  final String detail;
  final bool selected;

  @override
  Widget build(BuildContext context) => Expanded(
    child: Container(
      height: 88,
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: selected ? brandNavy : Colors.white.withValues(alpha: .82),
        borderRadius: BorderRadius.circular(18),
        border: selected ? null : Border.all(color: Colors.white),
      ),
      child: Row(
        children: [
          Icon(icon, color: selected ? Colors.white : brandTeal, size: 25),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: selected ? Colors.white : appInk,
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  detail,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: selected ? const Color(0xFFBFD6E3) : appMuted,
                    fontSize: 9,
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

class _TrackingScene extends StatelessWidget {
  const _TrackingScene();

  @override
  Widget build(BuildContext context) => Stack(
    children: [
      Positioned(
        left: 24,
        top: 27,
        bottom: 26,
        child: Container(
          width: 176,
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(21),
            boxShadow: const [
              BoxShadow(
                color: Color(0x140B3857),
                blurRadius: 20,
                offset: Offset(0, 10),
              ),
            ],
          ),
          child: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'On the way to you',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: appInk,
                  fontSize: 13,
                  fontWeight: FontWeight.w800,
                ),
              ),
              SizedBox(height: 12),
              _TimelineStep(label: 'China warehouse', complete: true),
              _TimelineStep(label: 'In transit', complete: true),
              _TimelineStep(label: 'Destination warehouse', isLast: true),
            ],
          ),
        ),
      ),
      Positioned(
        right: 20,
        bottom: 37,
        child: Container(
          width: 150,
          padding: const EdgeInsets.all(13),
          decoration: BoxDecoration(
            color: brandNavy,
            borderRadius: BorderRadius.circular(18),
            boxShadow: const [
              BoxShadow(
                color: Color(0x2E0B3857),
                blurRadius: 20,
                offset: Offset(0, 9),
              ),
            ],
          ),
          child: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    Icons.notifications_active_outlined,
                    color: Colors.white,
                    size: 21,
                  ),
                  Spacer(),
                  Icon(Icons.route_rounded, color: brandCoral, size: 25),
                ],
              ),
              SizedBox(height: 13),
              Text(
                'Milestone updated',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                ),
              ),
              SizedBox(height: 4),
              Text(
                'Your shipment is in transit',
                style: TextStyle(color: Color(0xFFBFD6E3), fontSize: 9),
              ),
            ],
          ),
        ),
      ),
    ],
  );
}

class _CollectionScene extends StatelessWidget {
  const _CollectionScene();

  @override
  Widget build(BuildContext context) => Stack(
    children: [
      Positioned(
        left: 23,
        top: 25,
        bottom: 25,
        child: Container(
          width: 202,
          padding: const EdgeInsets.all(15),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(21),
            boxShadow: const [
              BoxShadow(
                color: Color(0x140B3857),
                blurRadius: 20,
                offset: Offset(0, 10),
              ),
            ],
          ),
          child: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Choose your parcels',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: appInk,
                  fontSize: 13,
                  fontWeight: FontWeight.w800,
                ),
              ),
              SizedBox(height: 8),
              _ParcelChoice(label: 'Kitchen supplies'),
              SizedBox(height: 7),
              _ParcelChoice(label: 'Fabric order'),
              SizedBox(height: 7),
              _ParcelChoice(label: 'Shop display'),
            ],
          ),
        ),
      ),
      Positioned(
        right: 20,
        bottom: 30,
        child: Container(
          width: 145,
          padding: const EdgeInsets.all(13),
          decoration: BoxDecoration(
            color: brandNavy,
            borderRadius: BorderRadius.circular(18),
            boxShadow: const [
              BoxShadow(
                color: Color(0x2E0B3857),
                blurRadius: 20,
                offset: Offset(0, 9),
              ),
            ],
          ),
          child: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.qr_code_2_rounded, color: Colors.white, size: 30),
                  Spacer(),
                  _PersonAvatar(),
                ],
              ),
              SizedBox(height: 11),
              Text(
                'Ready to collect',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                ),
              ),
              SizedBox(height: 4),
              Text(
                'Use your QR code or PIN',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(color: Color(0xFFBFD6E3), fontSize: 9),
              ),
            ],
          ),
        ),
      ),
    ],
  );
}

class _ParcelChoice extends StatelessWidget {
  const _ParcelChoice({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Container(
    height: 36,
    padding: const EdgeInsets.symmetric(horizontal: 9),
    decoration: BoxDecoration(
      color: const Color(0xFFF5F7FA),
      borderRadius: BorderRadius.circular(11),
    ),
    child: Row(
      children: [
        Container(
          width: 18,
          height: 18,
          decoration: const BoxDecoration(
            color: brandTeal,
            shape: BoxShape.circle,
          ),
          child: const Icon(Icons.check_rounded, color: Colors.white, size: 12),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: appInk,
              fontSize: 10,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      ],
    ),
  );
}

class _TimelineStep extends StatelessWidget {
  const _TimelineStep({
    required this.label,
    this.complete = false,
    this.isLast = false,
  });

  final String label;
  final bool complete;
  final bool isLast;

  @override
  Widget build(BuildContext context) => SizedBox(
    height: isLast ? 30 : 39,
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Column(
          children: [
            Container(
              width: 18,
              height: 18,
              decoration: BoxDecoration(
                color: complete ? brandTeal : brandCoral,
                shape: BoxShape.circle,
              ),
              child: Icon(
                complete ? Icons.check_rounded : Icons.circle,
                size: complete ? 12 : 6,
                color: Colors.white,
              ),
            ),
            if (!isLast) Expanded(child: Container(width: 2, color: appBorder)),
          ],
        ),
        const SizedBox(width: 9),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.only(top: 1),
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: complete ? appMuted : appInk,
                fontSize: 10,
                fontWeight: complete ? FontWeight.w600 : FontWeight.w800,
              ),
            ),
          ),
        ),
      ],
    ),
  );
}
