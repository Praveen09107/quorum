/// The real, live `PUT /finance/budget` fetcher (`DEC-200`, product
/// rebuild). Matches `create_application_api.dart`'s own established
/// pattern -- a plain injected async function, a fresh access token
/// per call, since this route runs through the identical real Gate
/// pipeline under the hood.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';

/// A real, honest, minimal summary of what happened -- `executed` is
/// the real fact a caller needs to decide whether to show "updated" or
/// a genuine Gate rejection/revision. Mirrors `CreateApplicationResult`'s
/// own established "closed, not open-ended" shape.
class UpdateBudgetResult {
  final bool executed;
  final String decision;

  /// The real, final amount the Gate actually applied -- genuinely NOT
  /// always the same value the caller submitted: `UPDATE_BUDGET` is
  /// real `Stakes.S2`, so a real Judge revision can change it before
  /// execution. `null` only when `executed` is false (nothing real
  /// took effect at all).
  final double? amount;

  const UpdateBudgetResult({required this.executed, required this.decision, this.amount});
}

typedef UpdateBudgetFetcher = Future<UpdateBudgetResult> Function({
  required double amount,
  String? category,
});

UpdateBudgetFetcher createUpdateBudgetFetcher({
  required Future<String?> Function() getAccessToken,
  required http.Client client,
  String baseUrl = ApiConfig.baseUrl,
}) {
  return ({required double amount, String? category}) async {
    final accessToken = await getAccessToken();
    if (accessToken == null) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }

    final http.Response response;
    try {
      response = await client.put(
        Uri.parse('$baseUrl/finance/budget'),
        headers: {'Authorization': 'Bearer $accessToken', 'Content-Type': 'application/json'},
        body: jsonEncode({
          'amount': amount,
          if (category != null) 'category': category,
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
      throw ApiException(detail ?? "Couldn't update your budget -- try again.", statusCode: 502);
    }
    if (response.statusCode == 503) {
      throw const ApiException('The Gate\'s reviewer is temporarily unavailable -- please try again shortly.', statusCode: 503);
    }
    if (response.statusCode != 200) {
      throw ApiException('Could not update your budget right now.', statusCode: response.statusCode);
    }

    try {
      final json = jsonDecode(response.body) as Map<String, dynamic>;
      return UpdateBudgetResult(
        executed: json['executed'] as bool,
        decision: json['decision'] as String,
        amount: (json['amount'] as num?)?.toDouble(),
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
