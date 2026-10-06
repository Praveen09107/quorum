/// The real, live `POST /calendar/events` fetcher (`DEC-206`, product
/// rebuild). Matches `create_application_api.dart`'s/`update_budget_api
/// .dart`'s own established pattern -- a plain injected async function,
/// a fresh access token per call, the same real `401`/`502`/`503`
/// taxonomy, since this route runs through the identical real Gate
/// pipeline under the hood.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';

/// A real, honest, minimal summary of what happened. `eventStart`/
/// `eventEnd`/`eventTitle` are what the real caller needs to perform
/// the actual on-device `device_calendar` write -- never gated on
/// `executed`, since `CREATE_CALENDAR_EVENT_LOCAL` has no real
/// server-side execution branch at all (see `main.py`'s own
/// `_quick_capture_result_to_dict()` docstring for the full account).
class CreateCalendarEventResult {
  final bool executed;
  final String decision;
  final String? eventTitle;
  final DateTime? eventStart;
  final DateTime? eventEnd;

  const CreateCalendarEventResult({
    required this.executed,
    required this.decision,
    this.eventTitle,
    this.eventStart,
    this.eventEnd,
  });
}

typedef CreateCalendarEventFetcher = Future<CreateCalendarEventResult> Function({
  required String title,
  required DateTime start,
  required DateTime end,
  String? inviteeEmail,
});

CreateCalendarEventFetcher createCreateCalendarEventFetcher({
  required Future<String?> Function() getAccessToken,
  required http.Client client,
  String baseUrl = ApiConfig.baseUrl,
}) {
  return ({required String title, required DateTime start, required DateTime end, String? inviteeEmail}) async {
    final accessToken = await getAccessToken();
    if (accessToken == null) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }

    final http.Response response;
    try {
      response = await client.post(
        Uri.parse('$baseUrl/calendar/events'),
        headers: {'Authorization': 'Bearer $accessToken', 'Content-Type': 'application/json'},
        body: jsonEncode({
          'title': title,
          'start_iso': start.toUtc().toIso8601String(),
          'end_iso': end.toUtc().toIso8601String(),
          if (inviteeEmail != null) 'invitee_email': inviteeEmail,
        }),
      );
    } catch (e) {
      throw const ApiException('Could not reach Quorum -- check your connection and try again.');
    }

    if (response.statusCode == 401) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }
    if (response.statusCode == 502) {
      final detail = _tryParseDetail(response.body);
      throw ApiException(detail ?? "Couldn't book that event -- try again.", statusCode: 502);
    }
    if (response.statusCode == 503) {
      throw const ApiException('The Gate\'s reviewer is temporarily unavailable -- please try again shortly.', statusCode: 503);
    }
    if (response.statusCode != 200) {
      throw ApiException('Could not book that event right now.', statusCode: response.statusCode);
    }

    try {
      final json = jsonDecode(response.body) as Map<String, dynamic>;
      return CreateCalendarEventResult(
        executed: json['executed'] as bool,
        decision: json['decision'] as String,
        eventTitle: json['event_title'] as String?,
        eventStart: json['event_start'] == null ? null : DateTime.parse(json['event_start'] as String),
        eventEnd: json['event_end'] == null ? null : DateTime.parse(json['event_end'] as String),
      );
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }
  };
}

String? _tryParseDetail(String body) {
  try {
    final json = jsonDecode(body) as Map<String, dynamic>;
    return json['detail'] as String?;
  } catch (e) {
    return null;
  }
}
