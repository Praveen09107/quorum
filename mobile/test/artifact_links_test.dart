// Real tests for features/gate_pipeline/artifact_links.dart
// (`DEC-191`). Zero Flutter dependency -- `dart test` is the real
// verification.

import 'package:test/test.dart';
import 'package:quorum_mobile/features/gate_pipeline/artifact_links.dart';

void main() {
  group('gmailWebLink', () {
    test('builds the real #all/<id> permalink', () {
      expect(gmailWebLink('msg-123'), 'https://mail.google.com/mail/u/0/#all/msg-123');
    });
  });

  group('artifactLinkFor', () {
    test('returns null for a null artifact -- an honest absence', () {
      expect(artifactLinkFor(null), isNull);
    });

    test('returns null for an artifact with no recognized field', () {
      expect(artifactLinkFor({'unexpected': 'shape'}), isNull);
    });

    test('a draft artifact links to the real underlying message id, not the draft id', () {
      // Gmail's web client addresses a draft through its own nested
      // message id, not the draft wrapper id -- using draft_id here
      // would produce a broken link.
      final link = artifactLinkFor({'draft_id': 'draft-1', 'message_id': 'msg-1'});
      expect(link, isNotNull);
      expect(link!.url, 'https://mail.google.com/mail/u/0/#all/msg-1');
      expect(link.label, 'Open draft in Gmail');
    });

    test('a sent-message artifact (no draft_id) gets the plain Gmail label', () {
      final link = artifactLinkFor({'message_id': 'msg-2'});
      expect(link, isNotNull);
      expect(link!.label, 'Open in Gmail');
    });

    test('a calendar artifact uses the real, literal html_link verbatim, never reconstructed', () {
      final link = artifactLinkFor({'event_id': 'evt-1', 'html_link': 'https://calendar.google.com/event?eid=xyz'});
      expect(link, isNotNull);
      expect(link!.url, 'https://calendar.google.com/event?eid=xyz');
      expect(link.label, 'Open in Calendar');
    });

    test('an empty-string message_id is treated as absent, not a broken link', () {
      expect(artifactLinkFor({'message_id': ''}), isNull);
    });

    test('calendar is preferred when both shapes are somehow present', () {
      final link = artifactLinkFor({'html_link': 'https://calendar.google.com/event?eid=xyz', 'message_id': 'msg-1'});
      expect(link!.label, 'Open in Calendar');
    });
  });
}
