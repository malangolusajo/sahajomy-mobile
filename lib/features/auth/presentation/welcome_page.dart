import 'package:flutter/material.dart';

import '../../../core/ui/sahajomy_ui.dart';

class WelcomePage extends StatelessWidget {
  const WelcomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(24, 56, 24, 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SahajomyBrandMark(),
              const SizedBox(height: 40),
              const Text(
                'SAHAJOMY',
                style: TextStyle(
                  color: Color(0xFFFF6B4A),
                  fontSize: 14,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 2.5,
                ),
              ),
              const SizedBox(height: 12),
              const Text(
                'Ship smarter.\nGrow further.',
                style: TextStyle(
                  color: Color(0xFF0F3D5E),
                  fontSize: 36,
                  height: 1.15,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 18),
              const Text(
                'Container shipping and sourcing built around your business.',
                style: TextStyle(fontSize: 16, height: 1.75),
              ),
              const Spacer(),
              Row(
                children: [
                  Container(
                    width: 32,
                    height: 8,
                    decoration: BoxDecoration(
                      color: const Color(0xFFFF6B4A),
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                  const SizedBox(width: 8),
                  for (var i = 0; i < 2; i++) ...[
                    Container(
                      width: 8,
                      height: 8,
                      decoration: const BoxDecoration(
                        color: Color(0xFFE2E8F0),
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 8),
                  ],
                ],
              ),
              const SizedBox(height: 20),
              FilledButton(
                onPressed: () => Navigator.pushNamed(context, '/sign-in'),
                child: const Text('Get started'),
              ),
              const SizedBox(height: 6),
              Center(
                child: TextButton(
                  onPressed: () => Navigator.pushNamed(context, '/sign-in'),
                  child: const Text('I already have an account'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
