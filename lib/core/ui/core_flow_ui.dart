import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../network/api_exception.dart';

String coreFlowError(Object? error) {
  if (error is ApiException) return error.message;
  if (error is FormatException) return error.message;
  return 'Unable to connect. Check your connection and try again.';
}

const coreCanvas = Color(0xFFF5F7FA);
const coreInk = Color(0xFF141C30);
const coreNavy = Color(0xFF103B57);
const coreCoral = Color(0xFFFF6547);
const coreMuted = Color(0xFF627696);
const coreBorder = Color(0xFFDCE5F0);

/// The approved authentication/workspace layout, scoped to this flow.
class CoreFlowPage extends StatelessWidget {
  const CoreFlowPage({
    super.key,
    required this.title,
    required this.children,
    this.onBack,
    this.canGoBack = true,
    this.onRefresh,
  });
  final String title;
  final List<Widget> children;
  final VoidCallback? onBack;
  final bool canGoBack;
  final Future<void> Function()? onRefresh;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final content = ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
      padding: const EdgeInsets.fromLTRB(20, 18, 20, 32),
      children: children,
    );
    return Theme(
      data: theme.copyWith(
        scaffoldBackgroundColor: coreCanvas,
        textTheme: theme.textTheme.apply(
          bodyColor: coreInk,
          displayColor: coreInk,
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: Colors.white,
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 14,
            vertical: 14,
          ),
          hintStyle: const TextStyle(color: coreMuted, fontSize: 13),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(15),
            borderSide: const BorderSide(color: coreBorder),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(15),
            borderSide: const BorderSide(color: coreBorder),
          ),
        ),
        textButtonTheme: TextButtonThemeData(
          style: TextButton.styleFrom(
            foregroundColor: coreNavy,
            minimumSize: const Size(48, 48),
            textStyle: TextStyle(
              fontFamily: theme.textTheme.bodyMedium?.fontFamily,
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(
            backgroundColor: MediaQuery.highContrastOf(context)
                ? const Color(0xFFD3432A)
                : coreCoral,
            foregroundColor: Colors.white,
            minimumSize: const Size(double.infinity, 53),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
            textStyle: TextStyle(
              fontFamily: theme.textTheme.bodyMedium?.fontFamily,
              fontSize: 13,
              fontWeight: FontWeight.w700,
            ),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(15),
            ),
          ),
        ),
      ),
      child: Scaffold(
        appBar: AppBar(
          backgroundColor: coreCanvas,
          surfaceTintColor: Colors.transparent,
          toolbarHeight: MediaQuery.textScalerOf(context).scale(20) > 26
              ? MediaQuery.textScalerOf(context).scale(20) * 2 + 24
              : 64,
          titleSpacing: 6,
          centerTitle: false,
          automaticallyImplyLeading: false,
          leadingWidth: canGoBack ? 64 : 20,
          leading: canGoBack
              ? Padding(
                  padding: const EdgeInsets.only(left: 16, top: 8, bottom: 8),
                  child: IconButton.outlined(
                    style: IconButton.styleFrom(
                      backgroundColor: Colors.white,
                      side: const BorderSide(color: coreBorder),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(14),
                      ),
                    ),
                    tooltip: 'Back',
                    icon: const Icon(Icons.chevron_left, color: coreNavy),
                    onPressed:
                        onBack ??
                        () {
                          if (context.canPop()) {
                            context.pop();
                          } else {
                            context.go('/sign-in');
                          }
                        },
                  ),
                )
              : null,
          title: Text(
            title,
            maxLines: 2,
            style: TextStyle(
              fontFamily: theme.textTheme.bodyMedium?.fontFamily,
              fontSize: 20,
              fontWeight: FontWeight.w800,
              color: coreInk,
            ),
          ),
          bottom: const PreferredSize(
            preferredSize: Size.fromHeight(1),
            child: Divider(height: 1, color: coreBorder),
          ),
        ),
        body: SafeArea(
          top: false,
          child: onRefresh == null
              ? content
              : RefreshIndicator(onRefresh: onRefresh!, child: content),
        ),
      ),
    );
  }
}

class CoreHero extends StatelessWidget {
  const CoreHero({
    super.key,
    required this.eyebrow,
    required this.title,
    required this.description,
  });
  final String eyebrow, title, description;
  @override
  Widget build(BuildContext context) => Container(
    clipBehavior: Clip.antiAlias,
    decoration: BoxDecoration(
      color: coreNavy,
      borderRadius: BorderRadius.circular(26),
    ),
    child: Stack(
      children: [
        const Positioned(top: -100, right: -90, child: _HeroRings()),
        Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                eyebrow,
                style: const TextStyle(
                  color: Color(0xFFBBD5E3),
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 1.5,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                title,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 25,
                  height: 1.15,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 9),
              Text(
                description,
                style: const TextStyle(
                  color: Color(0xFFD9E6EE),
                  fontSize: 13,
                  height: 1.45,
                ),
              ),
              const SizedBox(height: 16),
              Container(
                width: 37,
                height: 4,
                decoration: BoxDecoration(
                  color: const Color(0xFFEFBF04),
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

class _HeroRings extends StatelessWidget {
  const _HeroRings();
  @override
  Widget build(BuildContext context) => Container(
    width: 224,
    height: 224,
    padding: const EdgeInsets.all(24),
    decoration: BoxDecoration(
      shape: BoxShape.circle,
      border: Border.all(
        color: Colors.white.withValues(alpha: .025),
        width: 24,
      ),
    ),
    child: Container(
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(
          color: Colors.white.withValues(alpha: .04),
          width: 24,
        ),
      ),
    ),
  );
}

class CoreField extends StatelessWidget {
  const CoreField({super.key, required this.label, required this.child});
  final String label;
  final Widget child;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w800,
            color: Color(0xFF374862),
          ),
        ),
        const SizedBox(height: 6),
        Semantics(label: label, child: child),
      ],
    ),
  );
}

class CoreError extends StatelessWidget {
  const CoreError(this.message, {super.key});
  final String message;
  @override
  Widget build(BuildContext context) => Semantics(
    liveRegion: true,
    child: Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Text(
        message,
        style: const TextStyle(color: Color(0xFFB42318), fontSize: 13),
      ),
    ),
  );
}

class CoreGroup extends StatelessWidget {
  const CoreGroup({super.key, required this.children});
  final List<Widget> children;
  @override
  Widget build(BuildContext context) => Material(
    color: Colors.white,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(20),
      side: const BorderSide(color: coreBorder),
    ),
    clipBehavior: Clip.antiAlias,
    child: Padding(
      padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 8),
      child: Column(
        children: [
          for (var i = 0; i < children.length; i++) ...[
            if (i > 0) const Divider(height: 1, color: coreBorder),
            children[i],
          ],
        ],
      ),
    ),
  );
}

class CoreChoice extends StatelessWidget {
  const CoreChoice({
    super.key,
    required this.title,
    required this.subtitle,
    required this.icon,
    this.selected = false,
    this.active = false,
    this.onTap,
  });
  final String title, subtitle;
  final IconData icon;
  final bool selected;
  final bool active;
  final VoidCallback? onTap;
  @override
  Widget build(BuildContext context) => ListTile(
    contentPadding: EdgeInsets.zero,
    minVerticalPadding: 8,
    leading: Container(
      width: 38,
      height: 38,
      decoration: BoxDecoration(
        color: selected ? const Color(0xFFFFEFEB) : const Color(0xFFEDF5F8),
        borderRadius: BorderRadius.circular(13),
      ),
      child: Icon(icon, color: selected ? coreCoral : coreNavy, size: 20),
    ),
    title: Text(
      title,
      style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
    ),
    subtitle: Text(
      subtitle,
      style: const TextStyle(fontSize: 11, color: coreMuted),
    ),
    selected: selected,
    trailing: selected
        ? const Icon(
            Icons.check_circle,
            color: Color(0xFF009B73),
            semanticLabel: 'Selected',
          )
        : active
        ? Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: const Color(0xFFE5F7F0),
              borderRadius: BorderRadius.circular(20),
            ),
            child: const Text(
              'Active',
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w700,
                color: Color(0xFF007B5A),
              ),
            ),
          )
        : onTap == null
        ? null
        : const Icon(Icons.chevron_right, color: coreMuted, size: 20),
    onTap: onTap,
  );
}
