// Real tests for features/email/email_overview_logic.dart. Zero
// Flutter dependencies, `dart test` is the real verification.

import 'package:test/test.dart';

import 'package:quorum_mobile/features/email/email_overview_logic.dart';

SentMessageData _message({DateTime? repliedAt}) {
  return SentMessageData(
    recipient: 'a@x.com',
    subject: 'a real subject',
    sentAt: DateTime(2026, 9, 1),
    repliedAt: repliedAt,
  );
}

void main() {
  group('isAwaitingReply / awaitingReply', () {
    test('a genuinely unreplied message is awaiting reply', () {
      expect(isAwaitingReply(_message(repliedAt: null)), isTrue);
    });

    test('a real, replied message is not awaiting reply', () {
      expect(isAwaitingReply(_message(repliedAt: DateTime(2026, 9, 2))), isFalse);
    });

    test('awaitingReply filters a real, mixed list down to only the genuinely unreplied ones', () {
      final messages = [_message(repliedAt: null), _message(repliedAt: DateTime(2026, 9, 2))];
      final result = awaitingReply(messages);
      expect(result.length, 1);
      expect(result.single.repliedAt, isNull);
    });

    test('an empty real list returns empty, not a crash', () {
      expect(awaitingReply([]), isEmpty);
    });
  });

  group('formatRelativeDays', () {
    final now = DateTime(2026, 10, 6, 12, 0, 0);

    test('today reads as Today', () {
      expect(formatRelativeDays(now, now), 'Today');
    });

    test('exactly one day ago reads as Yesterday', () {
      expect(formatRelativeDays(now.subtract(const Duration(days: 1)), now), 'Yesterday');
    });

    test('several days ago is a real, honest count', () {
      expect(formatRelativeDays(now.subtract(const Duration(days: 5)), now), '5 days ago');
    });
  });

  group('formatMessageCount', () {
    test('singular for exactly one', () {
      expect(formatMessageCount(1), '1 message');
    });

    test('plural for anything else, including zero', () {
      expect(formatMessageCount(0), '0 messages');
      expect(formatMessageCount(3), '3 messages');
    });
  });
}
