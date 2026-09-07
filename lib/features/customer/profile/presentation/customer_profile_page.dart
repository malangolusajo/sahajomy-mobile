import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../app/theme.dart';
import '../../../../core/auth/session_store.dart';
import '../../../../core/providers.dart';
import '../../presentation/customer_components.dart';
import '../../../auth/data/auth_repository.dart';
import '../../../public_services/presentation/official_information_page.dart';

class CustomerProfilePage extends ConsumerStatefulWidget {
  const CustomerProfilePage({super.key});

  @override
  ConsumerState<CustomerProfilePage> createState() =>
      _CustomerProfilePageState();
}

class _CustomerProfilePageState extends ConsumerState<CustomerProfilePage> {
  SessionStore get _store => ref.read(sessionStoreProvider);
  AuthRepository get _auth => ref.read(authRepositoryProvider);
  late Future<Map<String, dynamic>> _profile;

  @override
  void initState() {
    super.initState();
    _profile = _loadProfile();
  }

  Future<Map<String, dynamic>> _loadProfile() async {
    final session = await _store.read();
    if (session == null) throw StateError('Your session has expired.');
    return _auth.getProfile();
  }

  void _retry() => setState(() => _profile = _loadProfile());

  @override
  Widget build(BuildContext context) => CustomerScaffold(
    title: 'Profile',
    body: FutureBuilder<Map<String, dynamic>>(
      future: _profile,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return CustomerEmptyState(
            icon: Icons.person_outline,
            message: 'We could not load your profile.',
            actionLabel: 'Try again',
            onAction: _retry,
          );
        }
        final profile = snapshot.data!;
        final name = profile['name'] as String? ?? 'Sahajomy customer';
        final imageUrl = profile['profile_image_url'] as String?;
        final imageUri = imageUrl == null ? null : Uri.tryParse(imageUrl);
        final safeImageUrl =
            imageUri != null &&
                imageUri.scheme == 'https' &&
                imageUri.userInfo.isEmpty &&
                (imageUri.host == 'sahajomy.co.tz' ||
                    imageUri.host.endsWith('.sahajomy.co.tz'))
            ? imageUrl
            : null;
        final initials = name
            .split(' ')
            .where((part) => part.isNotEmpty)
            .take(2)
            .map((part) => part[0])
            .join()
            .toUpperCase();
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          children: [
            const CustomerHeroCard(
              eyebrow: 'Profile',
              title: 'Your profile',
              subtitle: 'View your verified account details and contact information.',
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                CircleAvatar(
                  radius: 32,
                  foregroundImage: safeImageUrl == null ? null : NetworkImage(safeImageUrl),
                  child: Text(initials.isEmpty ? 'S' : initials),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(name, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
                      Text(profile['email']?.toString() ?? 'No email provided', style: const TextStyle(color: appMuted)),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),
            _ProfileField(label: 'Mobile number', value: profile['phone_number']),
            _ProfileField(label: 'Account role', value: profile['role']),
            _ProfileField(label: 'Address', value: profile['address'] ?? 'Not provided'),
            _ProfileField(label: 'Account verification', value: profile['is_verified'] == true ? 'Verified' : 'Pending'),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: () => context.push('/customer/china-addresses'),
              child: const Text('Manage China warehouse addresses'),
            ),
            const SahajomyLegalLinks(),
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
