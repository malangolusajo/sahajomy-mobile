import 'package:flutter/material.dart';

const brandNavy = Color(0xFF0B3857);
const brandNavyDark = Color(0xFF062B44);
const brandCoral = Color(0xFFF36B4B);
const brandTeal = Color(0xFF11867A);
const appCanvas = Color(0xFFF5F7FA);
const appInk = Color(0xFF122230);
const appMuted = Color(0xFF607386);
const appBorder = Color(0xFFDDE5EC);

final ThemeData sahajomyTheme = ThemeData(
  useMaterial3: true,
  scaffoldBackgroundColor: appCanvas,
  colorScheme: ColorScheme.fromSeed(
    seedColor: brandNavy,
    primary: brandNavy,
    secondary: brandCoral,
    surface: Colors.white,
    error: const Color(0xFFB42318),
  ),
  appBarTheme: const AppBarTheme(
    backgroundColor: Colors.white,
    foregroundColor: brandNavy,
    elevation: 0,
    scrolledUnderElevation: .5,
    surfaceTintColor: Colors.transparent,
    centerTitle: true,
  ),
  filledButtonTheme: FilledButtonThemeData(
    style: FilledButton.styleFrom(
      backgroundColor: brandCoral,
      foregroundColor: Colors.white,
      minimumSize: const Size.fromHeight(54),
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      textStyle: const TextStyle(
        fontSize: 15,
        fontWeight: FontWeight.w800,
        letterSpacing: .1,
      ),
    ),
  ),
  outlinedButtonTheme: OutlinedButtonThemeData(
    style: OutlinedButton.styleFrom(
      foregroundColor: brandNavy,
      minimumSize: const Size.fromHeight(52),
      side: const BorderSide(color: appBorder),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
    ),
  ),
  textButtonTheme: TextButtonThemeData(
    style: TextButton.styleFrom(
      foregroundColor: brandNavy,
      textStyle: const TextStyle(fontWeight: FontWeight.w700),
    ),
  ),
  inputDecorationTheme: InputDecorationTheme(
    filled: true,
    fillColor: Colors.white,
    labelStyle: const TextStyle(color: appMuted, fontWeight: FontWeight.w600),
    hintStyle: const TextStyle(color: Color(0xFF94A3B8)),
    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(15),
      borderSide: const BorderSide(color: appBorder),
    ),
    enabledBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(15),
      borderSide: const BorderSide(color: appBorder),
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(15),
      borderSide: const BorderSide(color: brandNavy, width: 1.7),
    ),
  ),
  navigationBarTheme: const NavigationBarThemeData(
    backgroundColor: Colors.white,
    indicatorColor: Color(0xFFFFE7E0),
    labelTextStyle: WidgetStatePropertyAll(
      TextStyle(fontSize: 11, fontWeight: FontWeight.w700),
    ),
  ),
  cardTheme: CardThemeData(
    color: Colors.white,
    elevation: 0,
    margin: EdgeInsets.zero,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(20),
      side: const BorderSide(color: appBorder),
    ),
  ),
  dividerTheme: const DividerThemeData(color: appBorder, space: 1),
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
      letterSpacing: -.5,
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
    bodyLarge: TextStyle(fontSize: 16, height: 1.55, color: appMuted),
    bodyMedium: TextStyle(fontSize: 14, height: 1.5, color: appMuted),
    labelLarge: TextStyle(fontSize: 14, fontWeight: FontWeight.w800),
  ),
);
