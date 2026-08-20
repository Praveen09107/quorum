/// The real, live `TodayDataFetcher` implementation. Matches
/// `career_pipeline_api.dart`/`tasks_api.dart`'s already-established
/// pattern exactly: a plain injected async function, a fresh access
/// token read on every request, the same `ApiException` error
/// taxonomy.
///
/// Calls the real, live `GET /today` (`features/today.py`, `DEC-119`)
/// -- real per-user scoped from its first line, unlike the endpoints
/// this file's siblings originally wired. A real, disclosed, honest
/// fact, not a bug in this file: `pendingActions`/`negotiations` will
/// genuinely, correctly come back empty in real production use right
/// now -- nothing in this backend yet invokes the Gate against a real,
/// live user action to ever produce a row for either real table in the
/// first place.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';
import 'package:quorum_mobile/features/computed_state.dart';
import 'package:quorum_mobile/features/today/in_motion_logic.dart';
import 'package:quorum_mobile/features/today/needs_you_now_logic.dart';
import 'package:quorum_mobile/features/today_screen.dart';

Future<TodayScreenData> Function() createTodayFetcher({
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
        Uri.parse('$baseUrl/today'),
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
        'Could not load today right now.',
        statusCode: response.statusCode,
      );
    }

    final Map<String, dynamic> json;
    try {
      json = jsonDecode(response.body) as Map<String, dynamic>;
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }

    return _parseTodayScreenData(json);
  };
}

/// Fails CLOSED to `localMirror` on a genuinely unrecognized value --
/// the same fail-toward-less-confidence discipline already established
/// by `trust_logic.dart`'s `parseTarget()` and `trust_digest_logic.
/// dart`'s `parseTrend()`. The real, live backend always sends
/// `"live_backend"` (`today.py`'s own `source` field is a real,
/// hardcoded constant) -- an unrecognized value here would mean this
/// app is talking to something that isn't this backend's own real
/// `/today` route, and the honest response is to trust it less, not
/// silently claim it's live.
DataSource _parseDataSource(String raw) {
  return raw == 'live_backend' ? DataSource.liveBackend : DataSource.localMirror;
}

CapacityState _parseCapacityState(Map<String, dynamic> json) {
  return CapacityState(
    hoursRemainingToday: (json['hours_remaining_today'] as num).toDouble(),
    remainingFraction: (json['remaining_fraction'] as num).toDouble(),
    source: _parseDataSource(json['source'] as String),
  );
}

BudgetState _parseBudgetState(Map<String, dynamic> json) {
  return BudgetState(
    amountRemaining: (json['amount_remaining'] as num).toDouble(),
    remainingFraction: (json['remaining_fraction'] as num).toDouble(),
    source: _parseDataSource(json['source'] as String),
  );
}

PendingActionSummary _parsePendingAction(Map<String, dynamic> json) {
  return PendingActionSummary(
    proposalId: json['proposal_id'] as String,
    actionType: json['action_type'] as String,
    stakes: json['stakes'] as String,
    payload: json['payload'] as Map<String, dynamic>,
    createdAt: DateTime.parse(json['created_at'] as String),
  );
}

ActiveNegotiationSummary _parseActiveNegotiation(Map<String, dynamic> json) {
  return ActiveNegotiationSummary(
    negotiationId: json['negotiation_id'] as String,
    conflictedDomains: (json['conflicted_domains'] as List<dynamic>).cast<String>(),
    startedAt: DateTime.parse(json['started_at'] as String),
  );
}

TodayScreenData _parseTodayScreenData(Map<String, dynamic> json) {
  final pendingActions = (json['needs_you_now'] as List<dynamic>)
      .map((raw) => _parsePendingAction(raw as Map<String, dynamic>))
      .toList();
  final negotiations = (json['in_motion'] as List<dynamic>)
      .map((raw) => _parseActiveNegotiation(raw as Map<String, dynamic>))
      .toList();

  return TodayScreenData(
    pendingActions: pendingActions,
    capacity: _parseCapacityState(json['capacity'] as Map<String, dynamic>),
    budget: _parseBudgetState(json['budget'] as Map<String, dynamic>),
    negotiations: negotiations,
  );
}
