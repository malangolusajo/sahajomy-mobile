import 'package:flutter/material.dart';

class ShipmentTrackingPage extends StatelessWidget {
  const ShipmentTrackingPage({super.key});

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Track shipment')),
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
      children: [
        Text(
          'Shipment progress',
          style: Theme.of(context).textTheme.headlineMedium,
        ),
        const SizedBox(height: 6),
        const Text(
          'Follow your container from departure to delivery with the latest logistics updates.',
        ),
        const SizedBox(height: 24),
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: const Color(0xFF0F3D5E),
            borderRadius: BorderRadius.circular(16),
          ),
          child: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'CONTAINER',
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 1.2,
                  color: Color(0xFFBFDBFE),
                ),
              ),
              SizedBox(height: 6),
              Text(
                'MSKU 8392014',
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                  color: Colors.white,
                  fontFamily: 'monospace',
                ),
              ),
              SizedBox(height: 18),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('Shanghai', style: TextStyle(color: Colors.white)),
                  Text(
                    'In transit',
                    style: TextStyle(color: Color(0xFFFFB5A4)),
                  ),
                  Text('Dar es Salaam', style: TextStyle(color: Colors.white)),
                ],
              ),
              SizedBox(height: 10),
              LinearProgressIndicator(
                value: .6,
                minHeight: 6,
                color: Color(0xFFFF6B4A),
                backgroundColor: Color(0x33FFFFFF),
              ),
            ],
          ),
        ),
        const SizedBox(height: 28),
        const _TimelineRow(
          icon: Icons.check,
          color: Color(0xFF059669),
          title: 'Departed Shanghai',
          subtitle: '02 Aug, 09:30',
        ),
        const _TimelineRow(
          icon: Icons.circle,
          color: Color(0xFFFF6B4A),
          title: 'At sea',
          subtitle: 'Current location',
        ),
        const _TimelineRow(
          icon: Icons.circle_outlined,
          color: Color(0xFF94A3B8),
          title: 'Arrives Dar es Salaam',
          subtitle: '18 Aug, estimated',
        ),
        const SizedBox(height: 20),
        FilledButton(
          onPressed: () {},
          child: const Text('View shipment details'),
        ),
      ],
    ),
  );
}

class _TimelineRow extends StatelessWidget {
  const _TimelineRow({
    required this.icon,
    required this.color,
    required this.title,
    required this.subtitle,
  });
  final IconData icon;
  final Color color;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 20),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        CircleAvatar(
          radius: 14,
          backgroundColor: color.withValues(alpha: .14),
          child: Icon(icon, size: 16, color: color),
        ),
        const SizedBox(width: 12),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 2),
            Text(subtitle),
          ],
        ),
      ],
    ),
  );
}
