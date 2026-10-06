/// The real, live fetcher for `GET /today/summary` -- backs the
/// redesign's own new "This week across your agents" strip. Matches
/// `today_api.dart`'s own established fetcher pattern exactly.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';
import 'package:quorum_mobile/features/today/week_summary_logic.dart';

typedef WeekSummaryFetcher = Future<WeekSummaryData> Function();

WeekSummaryFetcher createWeekSummaryFetcher({
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
        Uri.parse('$baseUrl/today/summary'),
        headers: {'Authorization': 'Bearer $accessToken'},
      );
    } catch (e) {
      throw const ApiException('Could not reach Quorum -- check your connection and try again.');
    }

    if (response.statusCode == 401) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }
    if (response.statusCode == 503) {
      throw const ApiException('This week\'s summary is not currently available.', statusCode: 503);
    }
    if (response.statusCode != 200) {
      throw ApiException('Could not load this week\'s summary.', statusCode: response.statusCode);
    }

    final Map<String, dynamic> json;
    try {
      json = jsonDecode(response.body) as Map<String, dynamic>;
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }

    try {
      return WeekSummaryData(
        tasksDueThisWeek: json['tasks_due_this_week'] as int,
        monthToDateSpend: (json['month_to_date_spend'] as num).toDouble(),
        monthlyBudgetLimit: (json['monthly_budget_limit'] as num).toDouble(),
        applicationsInProgress: json['applications_in_progress'] as int,
        waitingOnCount: json['waiting_on_count'] as int,
      );
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }
  };
}
