import '../../../../core/auth/session_store.dart';
import '../../../../core/network/api_client.dart';

class CustomerAirCargoRepository {
  CustomerAirCargoRepository({this.client, SessionStore? sessionStore})
    : _store = sessionStore ?? SessionStore();

  final ApiClient? client;
  final SessionStore _store;

  Future<List<Map<String, dynamic>>> listBookings() =>
      (client ?? ApiClient(accessTokenProvider: _token)).getList(
        'customer/express-air-cargo/bookings',
      );

  Future<String?> _token() async => (await _store.read())?.accessToken;
}
