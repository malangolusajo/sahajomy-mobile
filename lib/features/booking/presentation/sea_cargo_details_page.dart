import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import '../../customer/presentation/customer_components.dart';
import 'components/booking_step_indicator.dart';

class SeaCargoDetailsPage extends ConsumerStatefulWidget {
  const SeaCargoDetailsPage({
    required this.containerId,
    required this.routeName,
    super.key,
  });

  final String containerId;
  final String routeName;

  @override
  ConsumerState<SeaCargoDetailsPage> createState() =>
      _SeaCargoDetailsPageState();
}

class _SeaCargoDetailsPageState extends ConsumerState<SeaCargoDetailsPage> {
  final _form = GlobalKey<FormState>();
  final _volume = TextEditingController();
  final _goodsType = TextEditingController();
  final _description = TextEditingController();
  final _quantity = TextEditingController();
  final _cartons = TextEditingController();

  String? _selectedGoodsType;
  final bool _busy = false;
  String? _error;

  static const _goodsTypes = [
    'Electronics',
    'Textiles & Clothing',
    'Machinery & Parts',
    'Furniture',
    'Toys & Games',
    'Auto Parts',
    'Building Materials',
    'Other',
  ];

  @override
  void dispose() {
    _volume.dispose();
    _goodsType.dispose();
    _description.dispose();
    _quantity.dispose();
    _cartons.dispose();
    super.dispose();
  }

  String? _required(String? v) => v == null || v.trim().length < 2
      ? 'Enter at least two characters.'
      : null;

  String? _volumeValidator(String? v) {
    final value = double.tryParse(v?.trim() ?? '');
    if (value == null || !value.isFinite || value <= 0) {
      return 'Enter a volume greater than zero.';
    }
    return null;
  }

  void _continueToReview() {
    if (!_form.currentState!.validate()) return;
    final params = {
      'container_id': widget.containerId,
      'route': widget.routeName,
      'volume': _volume.text.trim(),
      'goods_type': _selectedGoodsType ?? '',
      'description': _description.text.trim(),
      'quantity': _quantity.text.trim(),
      'cartons': _cartons.text.trim(),
    };
    context.push(
      '/customer/booking/sea-review?${Uri(queryParameters: params).query}',
    );
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Cargo details',
    body: AbsorbPointer(
      absorbing: _busy,
      child: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(24, 12, 24, 32),
          children: [
            const BookingStepIndicator(
              steps: ['Service', 'Cargo details', 'Review'],
              currentStep: 1,
            ),
            const SizedBox(height: 24),
            CustomerHeroCard(
              eyebrow: 'Sea freight',
              title: 'Cargo details',
              subtitle: widget.routeName,
            ),
            const SizedBox(height: 24),
            DropdownButtonFormField<String>(
              isExpanded: true,
              initialValue: _selectedGoodsType,
              decoration: const InputDecoration(labelText: 'Goods type'),
              items: _goodsTypes
                  .map((t) => DropdownMenuItem(value: t, child: Text(t)))
                  .toList(),
              onChanged: (v) => setState(() => _selectedGoodsType = v),
              validator: (v) => v == null ? 'Select a goods type.' : null,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _description,
              maxLines: 3,
              decoration: const InputDecoration(labelText: 'Goods description'),
              validator: _required,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _quantity,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Quantity'),
              validator: (v) {
                if (v == null || v.trim().isEmpty) return 'Enter quantity.';
                return (int.tryParse(v.trim()) ?? 0) > 0
                    ? null
                    : 'Enter a positive number.';
              },
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _volume,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              decoration: const InputDecoration(labelText: 'Volume (CBM)'),
              validator: _volumeValidator,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _cartons,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Carton count (optional)',
              ),
              validator: (v) {
                if (v == null || v.trim().isEmpty) return null;
                return (int.tryParse(v.trim()) ?? 0) > 0
                    ? null
                    : 'Enter a positive number.';
              },
            ),
            if (_error != null) ...[
              const SizedBox(height: 16),
              Text(_error!, style: const TextStyle(color: appError)),
            ],
            const SizedBox(height: 28),
            FilledButton(
              onPressed: _busy ? null : _continueToReview,
              child: const Text('Continue to review'),
            ),
            TextButton(
              onPressed: _busy ? null : () => context.pop(),
              child: const Text('Back to services'),
            ),
          ],
        ),
      ),
    ),
  );
}
