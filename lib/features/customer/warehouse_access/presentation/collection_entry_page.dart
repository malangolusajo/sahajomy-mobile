import 'package:flutter/material.dart';

import '../../presentation/customer_components.dart';
import 'customer_warehouse_parcels_page.dart';

class CollectionEntryPage extends StatefulWidget {
  const CollectionEntryPage({super.key});

  @override
  State<CollectionEntryPage> createState() => _CollectionEntryPageState();
}

class _CollectionEntryPageState extends State<CollectionEntryPage> {
  final _tokenController = TextEditingController();

  @override
  void dispose() {
    _tokenController.dispose();
    super.dispose();
  }

  void _openWarehouse() {
    final token = _tokenController.text.trim();
    if (token.isEmpty) return;
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => CustomerWarehouseParcelsPage(opaqueToken: token),
      ),
    );
  }

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Collection',
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      children: [
        const CustomerHeroCard(
          eyebrow: 'Warehouse',
          title: 'Collect your parcels',
          subtitle: 'Scan the warehouse QR code or enter the access token to view parcels ready for collection.',
        ),
        const SizedBox(height: 24),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Warehouse access token',
                  style: TextStyle(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: _tokenController,
                  decoration: const InputDecoration(
                    hintText: 'Paste or type the token from the QR code',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 16),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    onPressed: _openWarehouse,
                    child: const Text('View parcels'),
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFFF1F5F9),
            borderRadius: BorderRadius.circular(16),
          ),
          child: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'How collection works',
                style: TextStyle(fontWeight: FontWeight.w700),
              ),
              SizedBox(height: 8),
              Text('1. Visit your assigned Sahajomy warehouse.'),
              Text('2. Scan the warehouse QR code with your phone.'),
              Text('3. Select the parcels you want to collect.'),
              Text('4. Generate a collection code (QR + PIN) to show staff.'),
            ],
          ),
        ),
      ],
    ),
  );
}
