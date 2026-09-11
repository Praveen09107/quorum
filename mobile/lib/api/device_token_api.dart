/// The real, live `POST /device_token` implementation --
/// `QUORUM_FINAL_COMPLETION_PLAN.md` Session 9 (`DEC-176`). Matches
/// every other real fetcher's established injected-function pattern
/// exactly (`quick_capture_api.dart`'s own header comment has the full
/// account).
///
/// REAL, DISCLOSED SCOPE BOUNDARY, not an oversight: this file is
/// deliberately the ENTIRE real mobile half of Session 9 built tonight.
/// The real FCM SDK integration itself (`firebase_core`/
/// `firebase_messaging`, the real notification-permission request, the
/// real deep-link handler) was NOT added -- doing so would add a real
/// native Android Gradle dependency that needs a real
/// `google-services.json` tied to a real Firebase project to build
/// correctly at all. No real Firebase project exists in this
/// environment yet (see `backend/src/quorum_backend/features/fcm.py`'s
/// own top-of-file docstring for the full account) -- adding that
/// native dependency now would risk breaking the very next real
/// `flutter build`/`flutter run` for this app, for zero real,
/// verifiable benefit tonight, since nothing about it could actually be
/// tested without that real project anyway. This one function -- a
/// plain HTTP client with zero Firebase dependency -- is genuine,
/// useful, real progress that carries no such risk: once a real
/// `firebase_messaging`-obtained token exists, this is the real,
/// already-tested function that registers it.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';

Future<void> Function(String fcmToken) createDeviceTokenFetcher({
  required Future<String?> Function() getAccessToken,
  required http.Client client,
  String baseUrl = ApiConfig.baseUrl,
}) {
  return (String fcmToken) async {
    final accessToken = await getAccessToken();
    if (accessToken == null) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }

    final http.Response response;
    try {
      response = await client.post(
        Uri.parse('$baseUrl/device_token'),
        headers: {'Authorization': 'Bearer $accessToken', 'Content-Type': 'application/json'},
        body: jsonEncode({'fcm_token': fcmToken}),
      );
    } catch (e) {
      throw const ApiException('Could not reach Quorum -- check your connection and try again.');
    }

    if (response.statusCode == 401) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }
    if (response.statusCode == 422) {
      throw const ApiException('That device token was rejected.', statusCode: 422);
    }
    if (response.statusCode != 200) {
      throw ApiException('Could not register that device right now.', statusCode: response.statusCode);
    }
  };
}
