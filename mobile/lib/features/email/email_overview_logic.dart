// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Zero Flutter dependencies — plain Dart, `dart test` is
// the real verification.
//
// `DEC-199` (product rebuild) -- closes `DEC-197`'s own disclosed gap:
// Email has had no real workspace screen at all, only an honest "not
// built yet" SnackBar on the Agents tab. Backs `GET /email/overview`
// (`features/email_overview.py`) -- three real, already-existing
// sources (real Gmail drafts the agent created, real sent history,
// real known recipients) surfaced together for the first time.

class EmailDraftData {
  final String proposalId;
  final DateTime createdAt;
  final String recipient;
  final String? subject;
  final String? draftId;

  const EmailDraftData({
    required this.proposalId,
    required this.createdAt,
    required this.recipient,
    required this.subject,
    required this.draftId,
  });
}

class SentMessageData {
  final String recipient;
  final String subject;
  final DateTime sentAt;

  /// `null` means genuinely still unreplied -- never a fabricated
  /// distinct "no reply" state, matching `sent_messages.replied_at`'s
  /// own real, single meaning.
  final DateTime? repliedAt;

  const SentMessageData({
    required this.recipient,
    required this.subject,
    required this.sentAt,
    required this.repliedAt,
  });
}

class KnownRecipientData {
  final String recipient;
  final DateTime lastContactedAt;
  final int messageCount;

  const KnownRecipientData({
    required this.recipient,
    required this.lastContactedAt,
    required this.messageCount,
  });
}

class EmailOverviewData {
  final List<EmailDraftData> drafts;
  final List<SentMessageData> sentHistory;
  final List<KnownRecipientData> knownRecipients;

  const EmailOverviewData({
    required this.drafts,
    required this.sentHistory,
    required this.knownRecipients,
  });
}

bool isAwaitingReply(SentMessageData message) => message.repliedAt == null;

/// Pure, real filtering -- the "threads awaiting reply" the plan's own
/// Part B1 names, derived from the one real sent-history list rather
/// than a second real server round trip for a narrower view of the
/// exact same real rows.
List<SentMessageData> awaitingReply(List<SentMessageData> sentHistory) {
  return sentHistory.where(isAwaitingReply).toList();
}

/// Pure, real, coarse relative-day formatting -- a real OAuth/send
/// timestamp, not a live-updating clock, so a coarse real number is
/// honest where false precision would not be.
String formatRelativeDays(DateTime at, DateTime now) {
  final difference = now.difference(at);
  if (difference.inDays <= 0) return 'Today';
  if (difference.inDays == 1) return 'Yesterday';
  return '${difference.inDays} days ago';
}

/// Pure, real pluralization -- "1 message" vs "3 messages."
String formatMessageCount(int count) => count == 1 ? '1 message' : '$count messages';
