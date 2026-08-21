import 'package:flutter/material.dart';

const brandNavy = Color(0xFF0F3D5E);
const brandCoral = Color(0xFFFF6B4A);
const appCanvas = Color(0xFFF7F8FA);
const appInk = Color(0xFF0F172A);

final ThemeData sahajomyTheme = ThemeData(
  useMaterial3: true,
  scaffoldBackgroundColor: appCanvas,
  colorScheme: ColorScheme.fromSeed(
    seedColor: brandNavy,
    primary: brandNavy,
    secondary: brandCoral,
    surface: Colors.white,
  ),
  appBarTheme: const AppBarTheme(
    backgroundColor: Colors.white,
    foregroundColor: brandNavy,
    elevation: 0,
  ),
  filledButtonTheme: FilledButtonThemeData(
    style: FilledButton.styleFrom(
      backgroundColor: brandCoral,
      foregroundColor: Colors.white,
      minimumSize: const Size.fromHeight(52),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      textStyle: const TextStyle(fontWeight: FontWeight.w700),
    ),
  ),
  navigationBarTheme: const NavigationBarThemeData(
    backgroundColor: Colors.white,
    indicatorColor: Color(0xFFFFE2DB),
    labelTextStyle: WidgetStatePropertyAll(
      TextStyle(fontSize: 11, fontWeight: FontWeight.w700),
    ),
  ),
  cardTheme: CardThemeData(
    color: Colors.white,
    elevation: 0,
    margin: EdgeInsets.zero,
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
  ),
  dividerTheme: const DividerThemeData(color: Color(0xFFE2E8F0), space: 1),
  textTheme: const TextTheme(
    headlineMedium: TextStyle(
      fontSize: 30,
      height: 1.2,
      fontWeight: FontWeight.w800,
      color: brandNavy,
    ),
    titleLarge: TextStyle(
      fontSize: 20,
      height: 1.3,
      fontWeight: FontWeight.w700,
      color: appInk,
    ),
    bodyLarge: TextStyle(fontSize: 16, height: 1.5, color: Color(0xFF64748B)),
    bodyMedium: TextStyle(fontSize: 14, height: 1.45, color: Color(0xFF64748B)),
  ),
);
