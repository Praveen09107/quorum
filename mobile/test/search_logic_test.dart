// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this
// file was written. Zero Flutter dependencies (same as the file under
// test) — plain `package:test`, `dart test` is the real verification.

import 'package:test/test.dart';

import 'package:quorum_mobile/features/search/search_logic.dart';

void main() {
  group('parseItemType', () {
    test('email parses correctly', () {
      expect(parseItemType('email'), SearchItemType.email);
    });

    test('task parses correctly', () {
      expect(parseItemType('task'), SearchItemType.task);
    });

    test('expense parses correctly', () {
      expect(parseItemType('expense'), SearchItemType.expense);
    });

    test('decision parses correctly', () {
      expect(parseItemType('decision'), SearchItemType.decision);
    });

    test('a genuinely unrecognized value falls back to unknown, never a crash', () {
      expect(parseItemType('something_new'), SearchItemType.unknown);
    });
  });

  group('labelForItemType', () {
    test('email gets a real, readable label', () {
      expect(labelForItemType(SearchItemType.email), 'Email');
    });

    test('task gets a real, readable label', () {
      expect(labelForItemType(SearchItemType.task), 'Task');
    });

    test('expense gets a real, readable label', () {
      expect(labelForItemType(SearchItemType.expense), 'Expense');
    });

    test('decision gets a real, readable label', () {
      expect(labelForItemType(SearchItemType.decision), 'Decision');
    });

    test('unknown gets a generic but honest label, never a crash', () {
      expect(labelForItemType(SearchItemType.unknown), 'Result');
    });
  });

  test('every real SearchItemType value has a distinct, non-empty label', () {
    final labels = SearchItemType.values.map(labelForItemType).toSet();
    expect(labels.length, SearchItemType.values.length, reason: 'every type must have its own distinct label');
    expect(labels.every((l) => l.isNotEmpty), isTrue);
  });
}
