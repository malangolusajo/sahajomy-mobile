import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:sahajomy_mobile/core/network/api_client.dart';

void main() {
  test(
    'retries one protected request after refreshing an expired token',
    () async {
      var refreshCalls = 0;
      final requestTokens = <String?>[];
      final client = MockClient((request) async {
        requestTokens.add(request.headers['authorization']);
        if (request.headers['authorization'] == 'Bearer refreshed-token') {
          return http.Response('{"ok":true}', 200);
        }
        return http.Response('{"detail":"Expired token"}', 401);
      });
      final api = ApiClient(
        client: client,
        accessTokenProvider: () async => 'expired-token',
        refreshAccessToken: () async {
          refreshCalls++;
          return 'refreshed-token';
        },
      );

      final response = await api.get('protected-resource');

      expect(response['ok'], isTrue);
      expect(refreshCalls, 1);
      expect(requestTokens, ['Bearer expired-token', 'Bearer refreshed-token']);
    },
  );
}
