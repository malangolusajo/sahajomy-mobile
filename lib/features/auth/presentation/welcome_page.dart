import 'package:flutter/material.dart';

class WelcomePage extends StatelessWidget {
  const WelcomePage({super.key});

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(24, 32, 24, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 54,
                height: 54,
                decoration: BoxDecoration(
                  color: colors.primary,
                  borderRadius: BorderRadius.circular(18),
                ),
                child: const Icon(Icons.route_rounded, color: Colors.white),
              ),
              const Spacer(),
              Text('Sahajomy', style: Theme.of(context).textTheme.displaySmall),
              const SizedBox(height: 12),
              Text(
                'Your cargo journey, organized from booking to collection.',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 16),
              const Text(
                'Track shipments, manage reservations, and discover products in one secure place.',
              ),
              const Spacer(),
              FilledButton(
                onPressed: () => Navigator.pushNamed(context, '/sign-in'),
                style: FilledButton.styleFrom(
                  minimumSize: const Size.fromHeight(54),
                ),
                child: const Text('Sign in with phone number'),
              ),
              const SizedBox(height: 12),
              TextButton(
                onPressed: () => Navigator.pushNamed(context, '/customer'),
                child: const Text('Explore customer experience'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
