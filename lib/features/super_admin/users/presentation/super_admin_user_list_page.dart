import 'package:flutter/material.dart';

import '../data/super_admin_users_repository.dart';

class SuperAdminUserListPage extends StatefulWidget {
  const SuperAdminUserListPage({super.key});
  @override
  State<SuperAdminUserListPage> createState() => _SuperAdminUserListPageState();
}

class _SuperAdminUserListPageState extends State<SuperAdminUserListPage> {
  final _repository = SuperAdminUsersRepository();
  late Future<Map<String, dynamic>> _users = _repository.listUsers();
  void _retry() => setState(() => _users = _repository.listUsers());

  @override
  Widget build(BuildContext context) => FutureBuilder<Map<String, dynamic>>(
    future: _users,
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
      final users = (snapshot.data!['data'] as List? ?? const [])
          .cast<Map<String, dynamic>>();
      if (users.isEmpty) return const Center(child: Text('No users found.'));
      return ListView.separated(
        padding: const EdgeInsets.all(20),
        itemCount: users.length,
        separatorBuilder: (_, _) => const SizedBox(height: 10),
        itemBuilder: (_, index) {
          final user = users[index];
          return Card(
            child: ListTile(
              title: Text(user['name'] as String? ?? 'User'),
              subtitle: Text('${user['role']} | ${user['status']}'),
              trailing: Chip(
                label: Text(
                  user['is_verified'] == true ? 'Verified' : 'Pending',
                ),
              ),
            ),
          );
        },
      );
    },
  );
}
