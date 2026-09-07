import 'package:flutter/material.dart';

import 'theme.dart';

/// The approved onboarding theme remains separate from operational surfaces.
final operationalTheme = sahajomyTheme.copyWith(
  scaffoldBackgroundColor: appCanvas,
  appBarTheme: sahajomyTheme.appBarTheme.copyWith(
    backgroundColor: appCanvas,
    centerTitle: false,
    elevation: 0,
    scrolledUnderElevation: 0,
    titleTextStyle: const TextStyle(color: appInk, fontSize: 19, fontWeight: FontWeight.w800),
  ),
  cardTheme: const CardThemeData(
    color: Colors.white,
    elevation: 0,
    margin: EdgeInsets.zero,
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.all(Radius.circular(14))),
    clipBehavior: Clip.antiAlias,
  ),
  filledButtonTheme: FilledButtonThemeData(style: FilledButton.styleFrom(
    backgroundColor: brandNavy,
    foregroundColor: Colors.white,
    minimumSize: const Size(48, 52),
    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 15),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
    textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
  )),
  outlinedButtonTheme: OutlinedButtonThemeData(style: OutlinedButton.styleFrom(
    foregroundColor: brandNavy,
    minimumSize: const Size(48, 48),
    padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 13),
    side: const BorderSide(color: appBorder),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
  )),
  textButtonTheme: TextButtonThemeData(style: TextButton.styleFrom(
    foregroundColor: brandNavy,
    minimumSize: const Size(48, 48),
    textStyle: const TextStyle(fontWeight: FontWeight.w700),
  )),
  navigationBarTheme: NavigationBarThemeData(
    backgroundColor: Colors.white,
    surfaceTintColor: Colors.transparent,
    indicatorColor: brandCoralLight,
    height: 72,
    labelTextStyle: WidgetStateProperty.resolveWith((states) => TextStyle(
      color: states.contains(WidgetState.selected) ? brandNavy : appMuted,
      fontSize: 12,
      fontWeight: states.contains(WidgetState.selected) ? FontWeight.w800 : FontWeight.w500,
    )),
  ),
  textTheme: sahajomyTheme.textTheme.copyWith(
    headlineMedium: const TextStyle(fontSize: 30, height: 1.15, fontWeight: FontWeight.w800, letterSpacing: -.8, color: brandNavyDark),
    titleLarge: const TextStyle(fontSize: 20, height: 1.25, fontWeight: FontWeight.w800, color: appInk),
    bodyLarge: const TextStyle(fontSize: 16, height: 1.5, color: appInk),
    bodyMedium: const TextStyle(fontSize: 14, height: 1.5, color: appMuted),
  ),
  checkboxTheme: sahajomyTheme.checkboxTheme.copyWith(materialTapTargetSize: MaterialTapTargetSize.padded),
);
