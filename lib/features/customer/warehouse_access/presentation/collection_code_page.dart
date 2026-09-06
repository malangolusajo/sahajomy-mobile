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

class _CollectionCodePageState extends State<CollectionCodePage>
    with WidgetsBindingObserver {
  Timer? _timer;
  late final DateTime? _expiry;
  late String _collectionCode;
  late String _pin;
  late final int _parcelCount;
  Duration _remaining = Duration.zero;
  bool _revealed = true;

  bool get _expired => _expiry == null || _remaining <= Duration.zero;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _expiry = DateTime.tryParse('${widget.request['expires_at']}')?.toLocal();
    _collectionCode =
        '${widget.request['collection_code'] ?? widget.request['code'] ?? ''}';
    _pin = '${widget.request['pin'] ?? ''}';
    _parcelCount = int.tryParse('${widget.request['parcel_count'] ?? 0}') ?? 0;
    _tick();
    if (!_expired) {
      _timer = Timer.periodic(const Duration(seconds: 1), (_) => _tick());
    }
  }

  void _tick() {
    final expiry = _expiry;
    final remaining = expiry?.difference(DateTime.now()) ?? Duration.zero;
    if (!mounted) return;
    setState(() {
      _remaining = remaining;
      if (_expired) {
        _collectionCode = '';
        _pin = '';
        _revealed = false;
        _timer?.cancel();
      }
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed && mounted) {
      setState(() => _revealed = false);
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _timer?.cancel();
    _collectionCode = '';
    _pin = '';
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final minutes = _expired ? 0 : _remaining.inMinutes;
    final seconds = _expired ? 0 : _remaining.inSeconds.remainder(60);
    return Scaffold(
      appBar: const SahajomyScreenHeader(
        role: 'Collection request',
        title: 'Show warehouse staff',
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Icon(
            _expired ? Icons.timer_off_outlined : Icons.check_circle,
            color: _expired ? const Color(0xFFB42318) : const Color(0xFF047857),
            size: 40,
          ),
          const SizedBox(height: 12),
          Text(
            _expired
                ? 'Collection code expired'
                : '$_parcelCount parcels selected',
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 4),
          Text(
            _expired
                ? 'Return and create a new single-use request.'
                : 'Show this code only to authorised warehouse staff.',
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          if (!_expired && !_revealed)
            SahajomyMessageState(
              icon: Icons.visibility_off_outlined,
              message: 'Sensitive collection details are hidden.',
              actionLabel: 'Reveal securely',
              onAction: () => setState(() => _revealed = true),
            )
          else if (!_expired)
            Container(
              padding: const EdgeInsets.all(24),
              color: Colors.white,
              child: Column(
                children: [
                  Semantics(
                    label: 'Single-use collection QR code',
                    image: true,
                    child: QrImageView(
                      data: _collectionCode,
                      size: 176,
                      eyeStyle: const QrEyeStyle(color: appInk),
                      dataModuleStyle: const QrDataModuleStyle(color: appInk),
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
                          _pin,
                          style: const TextStyle(
                            fontSize: 36,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 8,
                            color: brandNavy,
                          ),
                        ),
                      ),
                      IconButton(
                        tooltip: 'Read collection PIN aloud',
                        onPressed: () => SemanticsService.sendAnnouncement(
                          View.of(context),
                          'Collection PIN $_pin',
                          TextDirection.ltr,
                        ),
                        icon: const Icon(Icons.volume_up_outlined),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          const SizedBox(height: 16),
          Text(
            _expired
                ? 'Expired'
                : 'Expires in ${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}',
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Color(0xFFB45309),
              fontWeight: FontWeight.w800,
            ),
          ),
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
