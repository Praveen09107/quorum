/// The real, live fetcher for `GET /connections` (`DEC-198`). Matches
/// `week_summary_api.dart`'s own established fetcher pattern exactly.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';
import 'package:quorum_mobile/features/connections/connections_logic.dart';

typedef ConnectionsFetcher = Future<ConnectionHealthData> Function();

ConnectionsFetcher createConnectionsFetcher({
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
        Uri.parse('$baseUrl/connections'),
        headers: {'Authorization': 'Bearer $accessToken'},
      );
    } catch (e) {
      throw const ApiException('Could not reach Quorum -- check your connection and try again.');
    }

    if (response.statusCode == 401) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }
    if (response.statusCode == 503) {
      throw const ApiException('Google connection status is not currently available.', statusCode: 503);
    }
    if (response.statusCode != 200) {
      throw ApiException('Could not load your Google connection status.', statusCode: response.statusCode);
    }

    final Map<String, dynamic> json;
    try {
      json = jsonDecode(response.body) as Map<String, dynamic>;
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }

    try {
      final lastUpdatedRaw = json['last_updated_at'] as String?;
      return ConnectionHealthData(
        connected: json['connected'] as bool,
        grantedScopes: (json['granted_scopes'] as List).cast<String>(),
        lastUpdatedAt: lastUpdatedRaw == null ? null : DateTime.parse(lastUpdatedRaw),
        tokenRefreshable: json['token_refreshable'] as bool?,
      );
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }
  };
}
