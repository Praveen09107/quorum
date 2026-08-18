// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this
// file was written. Zero Flutter dependencies (same as the file under
// test) — plain `package:test`, `dart test` is the real verification.
//
// HONEST DISCLOSURE: this repository never shipped a version of
// formatDeletionSummary with a hardcoded-plural "stores" bug -- built
// correct from the start, in one pass, matching this repository's real
// backend DeletionResult shape (a boolean sessions_revoked, not a
// device count -- see the file under test's own header comment for the
// full schema discrepancy disclosure against the batch guide's assumed
// shape). "a single real store is also genuinely singular" is included
// below as a genuine correctness property this function must have, not
// because a live regression was ever caught and fixed in this codebase.

import 'package:test/test.dart';

import 'package:quorum_mobile/features/you/you_logic.dart';

void main() {
  group('isValidDeletionConfirmation -- deliberately strict', () {
    test('the exact literal "DELETE" is valid', () {
      expect(isValidDeletionConfirmation('DELETE'), isTrue);
    });

    test('a lowercase near-match is rejected', () {
      expect(isValidDeletionConfirmation('delete'), isFalse);
    });

    test('leading whitespace is rejected, not trimmed', () {
      expect(isValidDeletionConfirmation(' DELETE'), isFalse);
    });

    test('trailing whitespace is rejected, not trimmed', () {
      expect(isValidDeletionConfirmation('DELETE '), isFalse);
    });

    test('a partial match is rejected', () {
      expect(isValidDeletionConfirmation('DEL'), isFalse);
    });

    test('an empty string is rejected', () {
      expect(isValidDeletionConfirmation(''), isFalse);
    });
  });

  group('formatDeletionSummary', () {
    test('a single real store is also genuinely singular -- "1 store", never "1 stores"', () {
      const result = DeletionResultData(
        sessionsRevoked: true,
        postgresRowsDeleted: 5,
        vectorEmbeddingsDeleted: 0,
        memoriesDeleted: 0,
        oauthTokensRevoked: 0,
      );

      final summary = formatDeletionSummary(result);
      expect(summary.contains('1 store.'), isTrue);
      expect(summary.contains('1 stores'), isFalse);
    });

    test('multiple real stores are correctly pluralized -- "stores", not "store"', () {
      const result = DeletionResultData(
        sessionsRevoked: true,
        postgresRowsDeleted: 5,
        vectorEmbeddingsDeleted: 340,
        memoriesDeleted: 3,
        oauthTokensRevoked: 2,
      );

      final summary = formatDeletionSummary(result);
      expect(summary.contains('4 stores'), isTrue);
      expect(summary.contains('4 store.'), isFalse);
    });

    test('session revocation states the real boolean fact, never a fabricated device count', () {
      const result = DeletionResultData(
        sessionsRevoked: true,
        postgresRowsDeleted: 1,
        vectorEmbeddingsDeleted: 0,
        memoriesDeleted: 0,
        oauthTokensRevoked: 0,
      );

      final summary = formatDeletionSummary(result);
      expect(summary.contains('signed out of every device'), isTrue);
    });
  });
}
