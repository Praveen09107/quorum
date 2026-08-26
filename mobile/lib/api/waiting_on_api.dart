/// The real, live `WaitingOnFetcher` implementation. Matches
/// `career_pipeline_api.dart`/`tasks_api.dart`'s already-established
/// pattern exactly: a plain injected async function, a fresh access
/// token read on every request, the same `ApiException` error taxonomy.
///
/// Calls the real, live `GET /waiting_on` (Phase 4, `features/
/// waiting_on.py`) -- the response is already pre-filtered server-side
/// to genuinely stale items only (`find_stale_waiting_on()`'s own real
/// 4-day threshold, `QUORUM_CONFIGURATION_CONSTANTS.md` §4); this file's
/// only job is parsing the real `{"recipient","subject","sent_at"}`
/// shape (`QUORUM_DATA_CONTRACTS.md` §5.9) into `WaitingOnItem`, never
/// re-deriving staleness on the client -- the same server-side-decision
/// discipline `waiting_on_logic.dart`'s own top-of-file comment already
/// established before any backend existed to call.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';
import 'package:quorum_mobile/features/waiting_on/waiting_on_logic.dart';

Future<List<WaitingOnItem>> Function() createWaitingOnFetcher({
  required Future<String?> Function() getAccessToken,
  required http.Client client,
  String baseUrl = ApiConfig.baseUrl,
}) {
  return () async {
    final accessToken = await getAccessToken();
    if (accessToken == null) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }

    final http.Response response;
    try {
      response = await client.get(
        Uri.parse('$baseUrl/waiting_on'),
        headers: {'Authorization': 'Bearer $accessToken'},
      );
    } catch (e) {
      throw const ApiException('Could not reach Quorum -- check your connection and try again.');
    }

    if (response.statusCode == 401) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }
    if (response.statusCode != 200) {
      throw ApiException(
        'Could not load what you are waiting on right now.',
        statusCode: response.statusCode,
      );
    }

    final List<dynamic> json;
    try {
      json = jsonDecode(response.body) as List<dynamic>;
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }

    return json.map((raw) => _parseWaitingOnItem(raw as Map<String, dynamic>)).toList();
  };
}

WaitingOnItem _parseWaitingOnItem(Map<String, dynamic> json) {
  return WaitingOnItem(
    recipient: json['recipient'] as String,
    subject: json['subject'] as String,
    sentAt: DateTime.parse(json['sent_at'] as String),
  );
}
