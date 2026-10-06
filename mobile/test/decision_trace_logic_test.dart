// Real tests for features/decision_trace/decision_trace_logic.dart
// (`DEC-201`, product rebuild). Zero Flutter dependencies, `dart test`
// is the real verification.

import 'package:test/test.dart';

import 'package:quorum_mobile/features/decision_trace/decision_trace_logic.dart';

void main() {
  group('computePayloadDiff', () {
    test('a real, changed value is reported with both before and after', () {
      final diff = computePayloadDiff({'amount': 60000.0}, {'amount': 55000.0});
      expect(diff.length, 1);
      expect(diff.single.key, 'amount');
      expect(diff.single.before, 60000.0);
      expect(diff.single.after, 55000.0);
    });

    test('a key the Judge genuinely added has no real before value', () {
      final diff = computePayloadDiff({'to': 'a@x.com'}, {'to': 'a@x.com', 'subject': 'Added'});
      expect(diff.single.key, 'subject');
      expect(diff.single.before, isNull);
      expect(diff.single.after, 'Added');
    });

    test('a key the Judge genuinely removed has no real after value', () {
      final diff = computePayloadDiff({'to': 'a@x.com', 'cc': 'b@x.com'}, {'to': 'a@x.com'});
      expect(diff.single.key, 'cc');
      expect(diff.single.before, 'b@x.com');
      expect(diff.single.after, isNull);
    });

    test('a key whose real value genuinely did not change is correctly excluded', () {
      final diff = computePayloadDiff({'to': 'a@x.com', 'amount': 100}, {'to': 'a@x.com', 'amount': 200});
      expect(diff.length, 1);
      expect(diff.single.key, 'amount');
    });

    test('two genuinely identical payloads produce an honestly empty diff', () {
      expect(computePayloadDiff({'a': 1}, {'a': 1}), isEmpty);
    });

    test('results are sorted by key for a deterministic, real display order', () {
      final diff = computePayloadDiff({'zebra': 1, 'alpha': 1}, {'zebra': 2, 'alpha': 2});
      expect(diff.map((e) => e.key).toList(), ['alpha', 'zebra']);
    });
  });

  group('formatDiffValue', () {
    test('a genuinely absent value reads as "(not set)", never a raw null', () {
      expect(formatDiffValue(null), '(not set)');
    });

    test('a real, present value is stringified as-is', () {
      expect(formatDiffValue(60000.0), '60000.0');
      expect(formatDiffValue('a real string'), 'a real string');
    });
  });

  group('formatActionType', () {
    test('a real snake_case action type becomes plain, title-cased English', () {
      expect(formatActionType('create_email_draft'), 'Create Email Draft');
      expect(formatActionType('update_budget'), 'Update Budget');
    });

    test('a single-word action type is still correctly capitalized', () {
      expect(formatActionType('send_email'), 'Send Email');
    });
  });
}
