/// The real, live `SearchFetcher` implementation. Matches
/// `career_pipeline_api.dart`/`tasks_api.dart`'s already-established
/// pattern exactly: a plain injected async function, a fresh access
/// token read on every request, the same `ApiException` error
/// taxonomy.
///
/// Calls the real, live `GET /search?q=...` (`features/search.py`,
/// Roadmap Phase 4a) -- real per-user scoped from its first line. A
/// real, disclosed, honest fact, not a bug in this file: the backend
/// lazily backfills any of this user's still-unembedded content on
/// every call, so a search shortly after new content exists can take
/// longer than a normal one -- a real, live Gemini call, not a bug.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';
import 'package:quorum_mobile/features/search/search_logic.dart';

Future<List<SearchResultItem>> Function(String query) createSearchFetcher({
  required Future<String?> Function() getAccessToken,
  required http.Client client,
  String baseUrl = ApiConfig.baseUrl,
}) {
  return (String query) async {
    final accessToken = await getAccessToken();
    if (accessToken == null) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }

    final http.Response response;
    try {
      response = await client.get(
        Uri.parse('$baseUrl/search').replace(queryParameters: {'q': query}),
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
        'Could not search right now.',
        statusCode: response.statusCode,
      );
    }

    final List<dynamic> json;
    try {
      json = jsonDecode(response.body) as List<dynamic>;
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }

    return json.map((raw) => _parseSearchResultItem(raw as Map<String, dynamic>)).toList();
  };
}

SearchResultItem _parseSearchResultItem(Map<String, dynamic> json) {
  return SearchResultItem(
    itemId: json['item_id'] as String,
    itemType: parseItemType(json['item_type'] as String),
    text: json['text'] as String,
    timestamp: DateTime.parse(json['timestamp'] as String),
  );
}
