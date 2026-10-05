/// The real, live fetcher for `GET /finance/expenses` -- the redesign's
/// own new "Finance hub" work. Matches `tasks_api.dart`'s own
/// established fetcher pattern exactly.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';
import 'package:quorum_mobile/features/finance/finance_logic.dart';

typedef ExpensesFetcher = Future<List<ExpenseData>> Function();

ExpensesFetcher createExpensesFetcher({
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
        Uri.parse('$baseUrl/finance/expenses'),
        headers: {'Authorization': 'Bearer $accessToken'},
      );
    } catch (e) {
      throw const ApiException('Could not reach Quorum -- check your connection and try again.');
    }

    if (response.statusCode == 401) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }
    if (response.statusCode != 200) {
      throw ApiException('Could not load your recent expenses.', statusCode: response.statusCode);
    }

    final List<dynamic> json;
    try {
      json = jsonDecode(response.body) as List<dynamic>;
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }

    try {
      return json.map((raw) {
        final item = raw as Map<String, dynamic>;
        return ExpenseData(
          expenseId: item['expense_id'] as String,
          payee: item['payee'] as String,
          amount: (item['amount'] as num).toDouble(),
          occurredAt: DateTime.parse(item['occurred_at'] as String),
        );
      }).toList();
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }
  };
}
