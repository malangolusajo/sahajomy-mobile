import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../../../../app/theme.dart';
import '../../../../core/ui/sahajomy_ui.dart';

class CollectionCodePage extends StatefulWidget {
  const CollectionCodePage({required this.request, super.key});

  final Map<String, dynamic> request;

  @override
  State<CollectionCodePage> createState() => _CollectionCodePageState();
}

class _CollectionCodePageState extends State<CollectionCodePage> {
  Timer? _timer;
  Duration _remaining = Duration.zero;

  @override
  void initState() {
    super.initState();
    final expiry = DateTime.tryParse('${widget.request['expires_at']}')
        ?.toLocal();
    if (expiry != null) {
      _remaining = expiry.difference(DateTime.now());
      _timer = Timer.periodic(const Duration(seconds: 1), (_) {
        if (mounted) {
          setState(() => _remaining = expiry.difference(DateTime.now()));
        }
      });
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final minutes = _remaining.isNegative ? 0 : _remaining.inMinutes;
    final seconds = _remaining.isNegative
        ? 0
        : _remaining.inSeconds.remainder(60);
    final expiry = DateTime.tryParse('${widget.request['expires_at']}')
        ?.toLocal();
    final collectionCode =
        '${widget.request['collection_code'] ?? widget.request['code'] ?? ''}';
    final pin = '${widget.request['pin'] ?? '------'}';
    return Scaffold(
      appBar: const SahajomyScreenHeader(
        role: 'Collection request',
        title: 'Show warehouse staff',
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          const Icon(Icons.check_circle, color: Color(0xFF047857), size: 40),
          const SizedBox(height: 12),
          Text(
            '${widget.request['parcel_count'] ?? 0} parcels selected',
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 4),
          const Text(
            'Show this code to warehouse staff.',
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          Container(
            padding: const EdgeInsets.all(24),
            color: Colors.white,
            child: Column(
              children: [
                Semantics(
                  label: 'Collection QR code. A text alternative is available below.',
                  image: true,
                  child: collectionCode.isEmpty
                      ? const Icon(
                          Icons.qr_code_2_rounded,
                          size: 176,
                          color: appInk,
                        )
                      : QrImageView(
                          data: collectionCode,
                          size: 176,
                          eyeStyle: const QrEyeStyle(color: appInk),
                          dataModuleStyle: const QrDataModuleStyle(
                            color: appInk,
                          ),
                        ),
                ),
                const SizedBox(height: 20),
                const Text(
                  'COLLECTION PIN',
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 2,
                  ),
                ),
                const SizedBox(height: 6),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    ExcludeSemantics(
                      child: Text(
                        pin,
                        style: const TextStyle(
                          fontSize: 36,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 8,
                          color: brandNavy,
                        ),
                      ),
                    ),
                    IconButton(
                      tooltip: 'Read collection PIN',
                      onPressed: () => SemanticsService.sendAnnouncement(
                        View.of(context),
                        'Collection PIN $pin',
                        TextDirection.ltr,
                      ),
                      icon: const Icon(Icons.volume_up_outlined),
                    ),
                  ],
                ),
                if (collectionCode.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  ExpansionTile(
                    tilePadding: EdgeInsets.zero,
                    title: const Text('Text alternative'),
                    children: [
                      SelectableText(
                        collectionCode,
                        textAlign: TextAlign.center,
                        style: const TextStyle(fontFamily: 'monospace'),
                      ),
                    ],
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 16),
          Text(
            'Expires in ${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}',
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Color(0xFFB45309),
              fontWeight: FontWeight.w800,
            ),
          ),
          if (expiry != null) ...[
            const SizedBox(height: 4),
            Text(
              'Valid until ${expiry.toString().substring(0, 16)}',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
          const SizedBox(height: 20),
          const SahajomySectionCard(
            title: 'Single use',
            children: [
              Text(
                'Staff must verify payment and physically hand over the selected parcels. You cannot mark them collected yourself.',
              ),
            ],
          ),
        ],
      ),
    );
  }
}
