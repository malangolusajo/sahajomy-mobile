import 'package:flutter/material.dart';

import '../../../../app/theme.dart';
import '../../../booking/presentation/booking_hub_page.dart';
import 'customer_home_page.dart';
import 'customer_agiza_page.dart';
import 'customer_tracking_page.dart';
import 'customer_account_page.dart';

class CustomerShell extends StatefulWidget {
  const CustomerShell({super.key});

  @override
  State<CustomerShell> createState() => _CustomerShellState();
}

class _CustomerShellState extends State<CustomerShell> {
  int _index = 0;
  final _visited = <int>{0};

  static const _pages = [
    CustomerHomePage(),
    BookingHubPage(),
    CustomerAgizaPage(),
    CustomerTrackingPage(),
    CustomerAccountPage(),
  ];

  @override
  Widget build(BuildContext context) => Scaffold(
    body: IndexedStack(
      index: _index,
      children: [
        for (var i = 0; i < _pages.length; i++)
          _visited.contains(i) ? _pages[i] : const SizedBox.shrink(),
      ],
    ),
    bottomNavigationBar: _CustomerBottomNav(
      selectedIndex: _index,
      onSelected: (i) => setState(() {
        _index = i;
        _visited.add(i);
      }),
    ),
  );
}

class _CustomerBottomNav extends StatelessWidget {
  const _CustomerBottomNav({
    required this.selectedIndex,
    required this.onSelected,
  });

  final int selectedIndex;
  final ValueChanged<int> onSelected;

  static const _items = [
    _NavItem(letter: 'H', label: 'Home'),
    _NavItem(letter: 'B', label: 'Book'),
    _NavItem(letter: 'A', label: 'Agiza'),
    _NavItem(letter: 'T', label: 'Tracking'),
    _NavItem(letter: 'M', label: 'Account'),
  ];

  @override
  Widget build(BuildContext context) => Container(
    decoration: const BoxDecoration(
      color: Colors.white,
      border: Border(top: BorderSide(color: appBorder)),
    ),
    padding: const EdgeInsets.only(top: 8, bottom: 20),
    child: SafeArea(
      top: false,
      child: Row(
        children: [
          for (var i = 0; i < _items.length; i++)
            Expanded(
              child: InkWell(
                onTap: () => onSelected(i),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 32,
                      height: 32,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: selectedIndex == i
                            ? brandCoral.withValues(alpha: 0.15)
                            : Colors.transparent,
                        shape: BoxShape.circle,
                      ),
                      child: Text(
                        _items[i].letter,
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w800,
                          color: selectedIndex == i ? brandCoral : appMuted,
                        ),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _items[i].label,
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: selectedIndex == i ? brandCoral : appMuted,
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    ),
  );
}

class _NavItem {
  const _NavItem({required this.letter, required this.label});
  final String letter;
  final String label;
}
