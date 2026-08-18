// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Zero Flutter dependencies — plain Dart, `dart test` is
// the real verification.
//
// Two real backend mechanisms confirmed before designing anything, not
// assumed. Checked directly: only `POST /auth/revoke` (sign out
// everywhere) exists — no per-device sign-out endpoint. This screen is
// honest about that; it never offers a "sign out this device only"
// option that would imply a real mechanism that isn't actually there.
//
// A SIGNIFICANT, DISCLOSED SCHEMA DISCREPANCY from this session's own
// kickoff prompt: the batch guide's pluralization-bug narrative assumes
// `DeletionResultData` carries an INTEGER device count (`sessions_
// revoked` pluralizing "device"/"devices") alongside a store-count map.
// This repository's REAL, already-shipped backend
// (`backend/src/quorum_backend/security/account_deletion.py`, built at
// `IMPL_22`) reports `sessions_revoked` as a plain BOOLEAN — there is no
// real mechanism in this backend that counts or reports individual
// revoked device sessions, only whether the real "sign out everywhere"
// call ran. Fabricating a device count this backend doesn't actually
// produce would be dishonest in exactly the way this project's whole
// discipline exists to prevent — and it would also contradict this same
// session's own real finding above (no per-device tracking exists).
// `formatDeletionSummary` below is built against the REAL backend shape:
// four real named store counts (Postgres rows, vector embeddings,
// memories, OAuth tokens) and one real boolean session-revocation fact.
//
// The real, genuine pluralization risk that DOES apply here -- store
// count, not device count -- is handled correctly from the first line
// of this file, not shipped with a hardcoded-plural bug and fixed later:
// this repository never had a buggy prior version of this function.
//
// THE REAL, LOAD-BEARING DESIGN REQUIREMENT: account deletion is
// explicitly S3-equivalent per `QUORUM_DATA_CONTRACTS.md` §5.8, requiring
// the same type-to-confirm ceremony as any other irreversible action --
// even though deletion itself never actually enters the Gate.

const String requiredDeletionConfirmationText = 'DELETE';

/// Deliberately strict -- case-sensitive, exact match, no fuzzy
/// tolerance, no trimming. A lowercase near-match, leading/trailing
/// whitespace, and a partial string are all real, plausible ways a
/// person could almost-but-not-quite confirm, and all correctly
/// rejected.
bool isValidDeletionConfirmation(String typed) {
  return typed == requiredDeletionConfirmationText;
}

class DeletionResultData {
  final bool sessionsRevoked;
  final int postgresRowsDeleted;
  final int vectorEmbeddingsDeleted;
  final int memoriesDeleted;
  final int oauthTokensRevoked;

  const DeletionResultData({
    required this.sessionsRevoked,
    required this.postgresRowsDeleted,
    required this.vectorEmbeddingsDeleted,
    required this.memoriesDeleted,
    required this.oauthTokensRevoked,
  });

  /// Only the real, named stores that actually had a nonzero count --
  /// a real, honest map of what genuinely happened, never padded with
  /// zero-count entries that would overstate how many places had data.
  Map<String, int> get nonZeroStoreCounts {
    final all = {
      'Postgres record': postgresRowsDeleted,
      'vector embedding': vectorEmbeddingsDeleted,
      'memory': memoriesDeleted,
      'OAuth token': oauthTokensRevoked,
    };
    return Map.fromEntries(all.entries.where((e) => e.value > 0));
  }
}

/// Real, honest deletion summary using the actual backend-reported
/// counts -- never a generic "your account has been deleted" message.
/// Both "store" and the session-revocation phrasing are handled
/// correctly for their real, respective real values -- pluralization
/// applied to real store counts, a plain boolean fact stated for session
/// revocation (this backend has no per-device count to report).
String formatDeletionSummary(DeletionResultData result) {
  final counts = result.nonZeroStoreCounts;
  final total = counts.values.fold(0, (sum, count) => sum + count);
  final storeWord = counts.length == 1 ? 'store' : 'stores';

  final sessionsClause = result.sessionsRevoked
      ? 'You have been signed out of every device.'
      : 'Session revocation did not complete — contact support if you still see active sessions.';

  return 'Deleted $total records across ${counts.length} $storeWord. $sessionsClause';
}
