/// The real, live `DeletionConfirmer` implementation. Matches
/// `finance_api.dart`/`career_pipeline_api.dart`'s already-established
/// pattern exactly: a plain injected async function, a fresh access
/// token read on every request, the same `ApiException` error
/// taxonomy.
///
/// Calls the real, live `DELETE /account` (`QUORUM_DATA_CONTRACTS.md`
/// §5.8, `DEC-113`) -- irreversible, S3-equivalent. The real,
/// type-to-confirm ceremony (`isValidDeletionConfirmation`,
/// `you_logic.dart`) is the real gate that runs before this fetcher is
/// ever called; this file performs no additional confirmation of its
/// own, trusting the same real access-token boundary every other
/// fetcher in this codebase already relies on.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';
import 'package:quorum_mobile/features/you/you_logic.dart';

Future<DeletionResultData> Function() createAccountDeletionConfirmer({
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
      response = await client.delete(
        Uri.parse('$baseUrl/account'),
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
        'Could not delete your account right now.',
        statusCode: response.statusCode,
      );
    }

    final Map<String, dynamic> json;
    try {
      json = jsonDecode(response.body) as Map<String, dynamic>;
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }

    return _parseDeletionResult(json);
  };
}

DeletionResultData _parseDeletionResult(Map<String, dynamic> json) {
  return DeletionResultData(
    sessionsRevoked: json['sessions_revoked'] as bool,
    postgresRowsDeleted: json['postgres_rows_deleted'] as int,
    vectorEmbeddingsDeleted: json['vector_embeddings_deleted'] as int,
    memoriesDeleted: json['memories_deleted'] as int,
    oauthTokensRevoked: json['oauth_tokens_revoked'] as int,
  );
}
