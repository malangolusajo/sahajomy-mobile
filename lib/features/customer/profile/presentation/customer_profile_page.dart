import 'package:flutter/material.dart';

import '../../../../core/auth/session_store.dart';
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
    appBar: AppBar(title: const Text('My profile')),
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
        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Center(
              child: CircleAvatar(
                radius: 40,
                foregroundImage: imageUrl == null || imageUrl.isEmpty
                    ? null
                    : NetworkImage(imageUrl),
                child: Text(name.isEmpty ? 'S' : name[0].toUpperCase()),
              ),
            ),
            const SizedBox(height: 14),
            Text(
              name,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 24),
            _ProfileField(
              label: 'Mobile number',
              value: profile['phone_number'],
            ),
            _ProfileField(label: 'Email', value: profile['email']),
            _ProfileField(label: 'Account role', value: profile['role']),
            _ProfileField(
              label: 'Verification',
              value: profile['is_verified'] == true ? 'Verified' : 'Pending',
            ),
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
