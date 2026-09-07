import 'package:flutter/material.dart';

// Sahajomy Brand Colors
const brandNavy = Color(0xFF0B3857);
const brandNavyDark = Color(0xFF062B44);
const brandCoral = Color(0xFFF36B4B);
const brandCoralLight = Color(0xFFFFE7E0);
const brandTeal = Color(0xFF11867A);
const brandTealLight = Color(0xFFE0F5F2);
const appCanvas = Color(0xFFF5F7FA);
const appInk = Color(0xFF122230);
const appMuted = Color(0xFF607386);
const appBorder = Color(0xFFDDE5EC);
const appSuccess = Color(0xFF059669);
const appWarning = Color(0xFFD97706);
const appError = Color(0xFFB42318);
const appErrorLight = Color(0xFFFFF1F0);

// Spacing scale (4px base unit)
const double spacingXs = 4;
const double spacingSm = 8;
const double spacingMd = 12;
const double spacingLg = 16;
const double spacingXl = 20;
const double spacing2xl = 24;
const double spacing3xl = 32;
const double spacing4xl = 40;

// Border radius scale
const double radiusSm = 8;
const double radiusMd = 12;
const double radiusLg = 16;
const double radiusXl = 20;
const double radius2xl = 24;
const double radiusRound = 999;

// Elevation/Shadows
const List<BoxShadow> shadowSm = [
  BoxShadow(
    color: Color(0x0A0B3857),
    blurRadius: 4,
    offset: Offset(0, 1),
  ),
];
const List<BoxShadow> shadowMd = [
  BoxShadow(
    color: Color(0x140B3857),
    blurRadius: 12,
    offset: Offset(0, 4),
  ),
];
const List<BoxShadow> shadowLg = [
  BoxShadow(
    color: Color(0x1A0B3857),
    blurRadius: 24,
    offset: Offset(0, 8),
  ),
];

// Animation durations
const Duration animFast = Duration(milliseconds: 150);
const Duration animNormal = Duration(milliseconds: 250);
const Duration animSlow = Duration(milliseconds: 350);

// Touch target minimum size
const double minTouchTarget = 48;

// Text styles (will be applied in ThemeData)
const TextStyle headingStyle = TextStyle(
  fontSize: 28,
  height: 1.12,
  fontWeight: FontWeight.w900,
  letterSpacing: -0.5,
);
const TextStyle titleStyle = TextStyle(
  fontSize: 20,
  height: 1.25,
  fontWeight: FontWeight.w800,
);
const TextStyle subtitleStyle = TextStyle(
  fontSize: 16,
  height: 1.3,
  fontWeight: FontWeight.w700,
);
const TextStyle bodyStyle = TextStyle(
  fontSize: 16,
  height: 1.55,
);
const TextStyle captionStyle = TextStyle(
  fontSize: 12,
  height: 1.4,
  fontWeight: FontWeight.w500,
);
const TextStyle labelStyle = TextStyle(
  fontSize: 13,
  fontWeight: FontWeight.w800,
  letterSpacing: 0.3,
);

// Input border radius
const BorderRadius inputBorderRadius = BorderRadius.all(Radius.circular(radiusLg));
const BorderRadius cardBorderRadius = BorderRadius.all(Radius.circular(radiusXl));
const BorderRadius buttonBorderRadius = BorderRadius.all(Radius.circular(radiusLg));
const BorderRadius chipBorderRadius = BorderRadius.all(Radius.circular(radiusRound));

final ThemeData sahajomyTheme = ThemeData(
  useMaterial3: true,
  scaffoldBackgroundColor: appCanvas,
  colorScheme: ColorScheme.fromSeed(
    seedColor: brandNavy,
    primary: brandNavy,
    secondary: brandCoral,
    tertiary: brandTeal,
    surface: Colors.white,
    error: appError,
    onPrimary: Colors.white,
    onSecondary: Colors.white,
    onSurface: appInk,
    onError: Colors.white,
  ),
  appBarTheme: const AppBarTheme(
    backgroundColor: Colors.white,
    foregroundColor: brandNavy,
    elevation: 0,
    scrolledUnderElevation: 0.5,
    surfaceTintColor: Colors.transparent,
    centerTitle: true,
    titleTextStyle: TextStyle(
      fontSize: 15,
      fontWeight: FontWeight.w800,
      color: Color(0xFF122230),
    ),
  ),
  filledButtonTheme: FilledButtonThemeData(
    style: FilledButton.styleFrom(
      backgroundColor: brandCoral,
      foregroundColor: Colors.white,
      minimumSize: const Size.fromHeight(54),
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: buttonBorderRadius),
      textStyle: const TextStyle(
        fontSize: 15,
        fontWeight: FontWeight.w800,
        letterSpacing: 0.1,
      ),
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
    ),
  ),
  outlinedButtonTheme: OutlinedButtonThemeData(
    style: OutlinedButton.styleFrom(
      foregroundColor: brandNavy,
      minimumSize: const Size.fromHeight(52),
      side: const BorderSide(color: appBorder, width: 1.5),
      shape: RoundedRectangleBorder(borderRadius: buttonBorderRadius),
      textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
    ),
  ),
  textButtonTheme: TextButtonThemeData(
    style: TextButton.styleFrom(
      foregroundColor: brandNavy,
      textStyle: const TextStyle(fontWeight: FontWeight.w700),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
    ),
  ),
  inputDecorationTheme: InputDecorationTheme(
    filled: true,
    fillColor: Colors.white,
    labelStyle: const TextStyle(color: appMuted, fontWeight: FontWeight.w600),
    hintStyle: const TextStyle(color: Color(0xFF94A3B8)),
    contentPadding: const EdgeInsets.symmetric(horizontal: spacingLg, vertical: spacingLg),
    border: OutlineInputBorder(
      borderRadius: inputBorderRadius,
      borderSide: const BorderSide(color: appBorder),
    ),
    enabledBorder: OutlineInputBorder(
      borderRadius: inputBorderRadius,
      borderSide: const BorderSide(color: appBorder),
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: inputBorderRadius,
      borderSide: const BorderSide(color: brandNavy, width: 2),
    ),
    errorBorder: OutlineInputBorder(
      borderRadius: inputBorderRadius,
      borderSide: const BorderSide(color: appError),
    ),
    focusedErrorBorder: OutlineInputBorder(
      borderRadius: inputBorderRadius,
      borderSide: const BorderSide(color: appError, width: 2),
    ),
    errorStyle: const TextStyle(
      color: appError,
      fontSize: 12,
      fontWeight: FontWeight.w600,
      height: 1.3,
    ),
    floatingLabelStyle: const TextStyle(
      color: brandNavy,
      fontWeight: FontWeight.w700,
    ),
    constraints: const BoxConstraints(minHeight: 56),
  ),
  navigationBarTheme: const NavigationBarThemeData(
    backgroundColor: Colors.white,
    indicatorColor: brandCoralLight,
    labelTextStyle: WidgetStatePropertyAll(
      TextStyle(fontSize: 11, fontWeight: FontWeight.w700),
    ),
    height: 72,
  ),
  cardTheme: CardThemeData(
    color: Colors.white,
    elevation: 0,
    margin: EdgeInsets.zero,
    shape: RoundedRectangleBorder(
      borderRadius: cardBorderRadius,
      side: const BorderSide(color: appBorder),
    ),
    clipBehavior: Clip.antiAlias,
  ),
  dividerTheme: const DividerThemeData(
    color: appBorder,
    space: 1,
    thickness: 1,
  ),
  listTileTheme: const ListTileThemeData(
    contentPadding: EdgeInsets.symmetric(horizontal: spacingLg, vertical: spacingSm),
    minLeadingWidth: 36,
    minTileHeight: 56,
    dense: false,
    shape: RoundedRectangleBorder(borderRadius: cardBorderRadius),
  ),
  chipTheme: ChipThemeData(
    backgroundColor: Colors.white,
    selectedColor: brandCoralLight,
    checkmarkColor: brandCoral,
    disabledColor: appBorder,
    labelStyle: const TextStyle(
      fontSize: 13,
      fontWeight: FontWeight.w600,
      color: appInk,
    ),
    secondaryLabelStyle: const TextStyle(
      fontSize: 13,
      fontWeight: FontWeight.w600,
      color: brandCoral,
    ),
    padding: const EdgeInsets.symmetric(horizontal: spacingMd, vertical: spacingSm),
    shape: RoundedRectangleBorder(
      borderRadius: chipBorderRadius,
      side: const BorderSide(color: appBorder),
    ),
    showCheckmark: true,
  ),
  badgeTheme: const BadgeThemeData(
    backgroundColor: brandCoral,
    textColor: Colors.white,
    textStyle: TextStyle(fontSize: 10, fontWeight: FontWeight.w800),
    largeSize: 18,
    smallSize: 14,
  ),
  textTheme: const TextTheme(
    displaySmall: TextStyle(
      fontSize: 38,
      height: 1.08,
      fontWeight: FontWeight.w900,
      letterSpacing: -1.2,
      color: brandNavyDark,
    ),
    headlineMedium: TextStyle(
      fontSize: 28,
      height: 1.12,
      fontWeight: FontWeight.w900,
      letterSpacing: -0.5,
      color: brandNavy,
    ),
    headlineSmall: TextStyle(
      fontSize: 23,
      height: 1.2,
      fontWeight: FontWeight.w800,
      color: appInk,
    ),
    titleLarge: TextStyle(
      fontSize: 20,
      height: 1.25,
      fontWeight: FontWeight.w800,
      color: appInk,
    ),
    titleMedium: TextStyle(
      fontSize: 16,
      height: 1.3,
      fontWeight: FontWeight.w700,
      color: appInk,
    ),
    titleSmall: TextStyle(
      fontSize: 14,
      height: 1.35,
      fontWeight: FontWeight.w700,
      color: appInk,
    ),
    bodyLarge: TextStyle(fontSize: 16, height: 1.55, color: appMuted),
    bodyMedium: TextStyle(fontSize: 14, height: 1.5, color: appMuted),
    bodySmall: TextStyle(fontSize: 12, height: 1.45, color: appMuted),
    labelLarge: TextStyle(fontSize: 14, fontWeight: FontWeight.w800, letterSpacing: 0.3),
    labelMedium: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, letterSpacing: 0.2),
    labelSmall: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, letterSpacing: 0.1),
  ),
  iconTheme: const IconThemeData(
    color: appMuted,
    size: 22,
  ),
  checkboxTheme: CheckboxThemeData(
    fillColor: WidgetStateProperty.resolveWith<Color>((states) {
      if (states.contains(WidgetState.selected)) return brandCoral;
      if (states.contains(WidgetState.disabled)) return appBorder;
      return Colors.transparent;
    }),
    checkColor: WidgetStateProperty.all(Colors.white),
    side: const BorderSide(color: appBorder, width: 2),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(radiusSm)),
    materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
  ),
  radioTheme: RadioThemeData(
    fillColor: WidgetStateProperty.resolveWith<Color>((states) {
      if (states.contains(WidgetState.selected)) return brandCoral;
      if (states.contains(WidgetState.disabled)) return appBorder;
      return appBorder;
    }),
  ),
  switchTheme: SwitchThemeData(
    thumbColor: WidgetStateProperty.resolveWith<Color>((states) {
      if (states.contains(WidgetState.selected)) return brandCoral;
      if (states.contains(WidgetState.disabled)) return appMuted;
      return Colors.grey.shade400;
    }),
    trackColor: WidgetStateProperty.resolveWith<Color>((states) {
      if (states.contains(WidgetState.selected)) return brandCoralLight;
      if (states.contains(WidgetState.disabled)) return appBorder;
      return appBorder;
    }),
    trackOutlineColor: WidgetStateProperty.resolveWith<Color?>((states) {
      if (states.contains(WidgetState.disabled)) return appBorder;
      return null;
    }),
  ),
  progressIndicatorTheme: const ProgressIndicatorThemeData(
    color: brandCoral,
    linearTrackColor: appBorder,
    circularTrackColor: appBorder,
  ),
  sliderTheme: SliderThemeData(
    activeTrackColor: brandCoral,
    inactiveTrackColor: appBorder,
    thumbColor: brandCoral,
    overlayColor: brandCoralLight,
    valueIndicatorColor: brandNavy,
    valueIndicatorTextStyle: const TextStyle(color: Colors.white, fontSize: 12),
    activeTickMarkColor: brandCoral,
    inactiveTickMarkColor: appMuted,
    trackHeight: 4,
    thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 10),
  ),
  tabBarTheme: const TabBarThemeData(
    labelColor: brandNavy,
    unselectedLabelColor: appMuted,
    indicatorColor: brandCoral,
    indicatorSize: TabBarIndicatorSize.label,
    labelStyle: TextStyle(fontSize: 14, fontWeight: FontWeight.w800),
    unselectedLabelStyle: TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
    dividerColor: Colors.transparent,
  ),
  bottomSheetTheme: const BottomSheetThemeData(
    backgroundColor: Colors.white,
    modalBackgroundColor: Colors.white,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(radius2xl)),
    ),
    clipBehavior: Clip.antiAlias,
    elevation: 8,
  ),
  dialogTheme: const DialogThemeData(
    backgroundColor: Colors.white,
    surfaceTintColor: Colors.transparent,
    elevation: 8,
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.all(Radius.circular(radius2xl))),
    titleTextStyle: TextStyle(
      fontSize: 20,
      fontWeight: FontWeight.w800,
      color: appInk,
    ),
    contentTextStyle: TextStyle(
      fontSize: 14,
      height: 1.5,
      color: appMuted,
    ),
  ),
  snackBarTheme: SnackBarThemeData(
    backgroundColor: appInk,
    contentTextStyle: const TextStyle(color: Colors.white, fontSize: 14),
    actionTextColor: brandCoral,
    behavior: SnackBarBehavior.floating,
    shape: RoundedRectangleBorder(borderRadius: cardBorderRadius),
    elevation: 4,
  ),
  tooltipTheme: TooltipThemeData(
    decoration: BoxDecoration(
      color: appInk.withValues(alpha: 0.95),
      borderRadius: BorderRadius.circular(radiusMd),
    ),
    textStyle: const TextStyle(color: Colors.white, fontSize: 12),
    padding: const EdgeInsets.symmetric(horizontal: spacingMd, vertical: spacingSm),
    verticalOffset: 8,
  ),
  scrollbarTheme: ScrollbarThemeData(
    thumbColor: WidgetStateProperty.all(appMuted.withValues(alpha: 0.5)),
    trackColor: WidgetStateProperty.all(Colors.transparent),
    thickness: const WidgetStatePropertyAll(4),
    radius: const Radius.circular(radiusRound),
    crossAxisMargin: 4,
    mainAxisMargin: 4,
  ),
);
