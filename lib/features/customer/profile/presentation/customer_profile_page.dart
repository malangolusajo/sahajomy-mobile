import 'package:flutter/material.dart';

import '../../../../core/auth/session_store.dart';
import '../../../../core/ui/sahajomy_ui.dart';
import '../../../auth/data/auth_repository.dart';

class CustomerProfilePage extends StatefulWidget {
  const CustomerProfilePage({super.key});

  @override
  State<CustomerProfilePage> createState() => _CustomerProfilePageState();
}

class _CustomerProfilePageState extends State<CustomerProfilePage> {
  final _store = SessionStore();
  final _auth = AuthRepository();
  late Future<Map<String, dynamic>> _profile = _loadProfile();

  Future<Map<String, dynamic>> _loadProfile() async {
    final session = await _store.read();
    if (session == null) throw StateError('Your session has expired.');
    return _auth.getProfile(session);
  }

  void _retry() => setState(() => _profile = _loadProfile());

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const SahajomyScreenHeader(role: 'Customer', title: 'Profile'),
    body: FutureBuilder<Map<String, dynamic>>(
      future: _profile,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return Center(
            child: OutlinedButton(
              onPressed: _retry,
              child: const Text('Try again'),
            ),
          );
        }
        final profile = snapshot.data!;
        final name = profile['name'] as String? ?? 'Sahajomy customer';
        final imageUrl = profile['profile_image_url'] as String?;
        final initials = name
            .split(' ')
            .where((part) => part.isNotEmpty)
            .take(2)
            .map((part) => part[0])
            .join()
            .toUpperCase();
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
          children: [
            Text(name, style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 4),
            Text(
              'Customer account · ${profile['email'] ?? 'No email provided'}',
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                CircleAvatar(
                  radius: 32,
                  foregroundImage: imageUrl == null || imageUrl.isEmpty
                      ? null
                      : NetworkImage(imageUrl),
                  child: Text(initials.isEmpty ? 'S' : initials),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(name, style: Theme.of(context).textTheme.titleLarge),
                      Text(profile['email']?.toString() ?? 'No email provided'),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),
            _ProfileField(
              label: 'Personal details',
              value: profile['phone_number'],
            ),
            _ProfileField(label: 'Business details', value: profile['role']),
            _ProfileField(
              label: 'Saved addresses',
              value: profile['address'] ?? 'Manage delivery addresses',
            ),
            _ProfileField(
              label: 'Security and privacy',
              value: profile['is_verified'] == true ? 'Verified' : 'Pending',
            ),
            const SizedBox(height: 12),
            FilledButton(onPressed: () {}, child: const Text('Edit profile')),
          ],
        );
      },
    ),
  );
}

class _ProfileField extends StatelessWidget {
  const _ProfileField({required this.label, required this.value});

  final String label;
  final Object? value;

  @override
  Widget build(BuildContext context) => Card(
    child: ListTile(
      title: Text(label),
      subtitle: Text(value?.toString() ?? 'Not provided'),
    ),
  );
}
