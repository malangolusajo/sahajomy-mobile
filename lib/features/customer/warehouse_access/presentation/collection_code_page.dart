import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../../../../app/theme.dart';
import '../../../../core/ui/sahajomy_ui.dart';
import '../../presentation/customer_components.dart';

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
    return CustomerScaffold(
      title: 'Collection QR / PIN',
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
        children: [
          CustomerHeroCard(
            eyebrow: _expired ? 'Expired' : 'Ready for collection',
            title: 'Collection code',
            subtitle: _expired
                ? 'This code has expired. Create a new single-use request to collect your goods.'
                : 'Show this single-use code when collecting your goods.',
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
            Column(
              children: [
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: appBorder),
                  ),
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
                  '$_parcelCount parcels · Expires ${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')} · Single use',
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 13, color: appMuted),
                ),
                const SizedBox(height: 20),
                OutlinedButton.icon(
                  onPressed: () {},
                  icon: const Icon(Icons.brightness_high_outlined),
                  label: const Text('Maximize brightness'),
                ),
              ],
            ),
          if (_expired) ...[
            const SizedBox(height: 24),
            Icon(Icons.timer_off_outlined, size: 48, color: appError),
            const SizedBox(height: 12),
            const Text(
              'Collection code expired',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
            ),
          ],
        ],
      ),
    );
  }
}
