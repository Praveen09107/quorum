/// The real, live fetcher for `GET /email/overview` (`DEC-199`).
/// Matches `week_summary_api.dart`'s own established fetcher pattern
/// exactly.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';
import 'package:quorum_mobile/features/email/email_overview_logic.dart';

typedef EmailOverviewFetcher = Future<EmailOverviewData> Function();

EmailOverviewFetcher createEmailOverviewFetcher({
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
        Uri.parse('$baseUrl/email/overview'),
        headers: {'Authorization': 'Bearer $accessToken'},
      );
    } catch (e) {
      throw const ApiException('Could not reach Quorum -- check your connection and try again.');
    }

    if (response.statusCode == 401) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }
    if (response.statusCode != 200) {
      throw ApiException('Could not load your real email activity.', statusCode: response.statusCode);
    }

    final Map<String, dynamic> json;
    try {
      json = jsonDecode(response.body) as Map<String, dynamic>;
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }

    try {
      return EmailOverviewData(
        drafts: (json['drafts'] as List).map((raw) {
          final d = raw as Map<String, dynamic>;
          return EmailDraftData(
            proposalId: d['proposal_id'] as String,
            createdAt: DateTime.parse(d['created_at'] as String),
            recipient: d['recipient'] as String,
            subject: d['subject'] as String?,
            draftId: d['draft_id'] as String?,
          );
        }).toList(),
        sentHistory: (json['sent_history'] as List).map((raw) {
          final m = raw as Map<String, dynamic>;
          final repliedAtRaw = m['replied_at'] as String?;
          return SentMessageData(
            recipient: m['recipient'] as String,
            subject: m['subject'] as String,
            sentAt: DateTime.parse(m['sent_at'] as String),
            repliedAt: repliedAtRaw == null ? null : DateTime.parse(repliedAtRaw),
          );
        }).toList(),
        knownRecipients: (json['known_recipients'] as List).map((raw) {
          final r = raw as Map<String, dynamic>;
          return KnownRecipientData(
            recipient: r['recipient'] as String,
            lastContactedAt: DateTime.parse(r['last_contacted_at'] as String),
            messageCount: r['message_count'] as int,
          );
        }).toList(),
      );
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }
  };
}
