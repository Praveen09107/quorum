/// The real, live approve/reject fetchers -- closes a real, previously-
/// undiscovered gap: `GateRevealScreen` has always been read-only;
/// `POST /actions/{id}/approve`/`POST /actions/{id}/reject` are the
/// first real backend routes letting a signed-in user actually act on
/// a pending "Needs you now" item. Matches `negotiation_api.dart`'s own
/// established parameterized-fetcher pattern exactly.
///
/// `409`/`502`/`503` each carry a real, specific `detail` string from
/// the backend (e.g. "Your Google account needs to be reconnected
/// before this can be approved.") -- surfaced verbatim, the same
/// established pattern `quick_capture_api.dart::_tryParseDetail`
/// already uses, rather than collapsed into one generic error.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';

typedef ApproveActionCall = Future<void> Function(String proposalId);
typedef RejectActionCall = Future<void> Function(String proposalId);

String? _tryParseDetail(String body) {
  try {
    final json = jsonDecode(body) as Map<String, dynamic>;
    return json['detail'] as String?;
  } catch (e) {
    return null;
  }
}

ApproveActionCall createApproveActionFetcher({
  required Future<String?> Function() getAccessToken,
  required http.Client client,
  String baseUrl = ApiConfig.baseUrl,
}) {
  return (String proposalId) async {
    final accessToken = await getAccessToken();
    if (accessToken == null) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }

    final http.Response response;
    try {
      response = await client.post(
        Uri.parse('$baseUrl/actions/${Uri.encodeComponent(proposalId)}/approve'),
        headers: {'Authorization': 'Bearer $accessToken'},
      );
    } catch (e) {
      throw const ApiException('Could not reach Quorum -- check your connection and try again.');
    }

    if (response.statusCode == 200) return;
    if (response.statusCode == 401) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }
    if (response.statusCode == 404) {
      throw const ApiException('This action could not be found.', statusCode: 404);
    }
    if (response.statusCode == 409) {
      final detail = _tryParseDetail(response.body);
      throw ApiException(detail ?? 'This action cannot be approved right now.', statusCode: 409);
    }
    if (response.statusCode == 502) {
      final detail = _tryParseDetail(response.body);
      throw ApiException(detail ?? 'Approving this did not succeed -- try again.', statusCode: 502);
    }
    if (response.statusCode == 503) {
      final detail = _tryParseDetail(response.body);
      throw ApiException(detail ?? 'Approving a real action is not currently available.', statusCode: 503);
    }
    throw ApiException('Could not approve this right now.', statusCode: response.statusCode);
  };
}

RejectActionCall createRejectActionFetcher({
  required Future<String?> Function() getAccessToken,
  required http.Client client,
  String baseUrl = ApiConfig.baseUrl,
}) {
  return (String proposalId) async {
    final accessToken = await getAccessToken();
    if (accessToken == null) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }

    final http.Response response;
    try {
      response = await client.post(
        Uri.parse('$baseUrl/actions/${Uri.encodeComponent(proposalId)}/reject'),
        headers: {'Authorization': 'Bearer $accessToken'},
      );
    } catch (e) {
      throw const ApiException('Could not reach Quorum -- check your connection and try again.');
    }

    if (response.statusCode == 200) return;
    if (response.statusCode == 401) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }
    if (response.statusCode == 404) {
      throw const ApiException('This action could not be found.', statusCode: 404);
    }
    if (response.statusCode == 409) {
      final detail = _tryParseDetail(response.body);
      throw ApiException(detail ?? 'This action has already been resolved.', statusCode: 409);
    }
    throw ApiException('Could not dismiss this right now.', statusCode: response.statusCode);
  };
}
