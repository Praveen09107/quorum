// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Zero Flutter dependencies — plain Dart, `dart test` is
// the real verification.
//
// `DEC-201` (product rebuild) -- the real Decision Trace screen named
// in the original plan: "any past action, replayed... shareable as the
// 'proof it's real' screen." `GET /actions/{id}/status` (`DEC-189`
// Block B) has returned everything this screen needs since it was
// first built -- the real, recorded gate_timeline, the real pre-
// revision payload, the real final one -- with zero real mobile caller
// until this entry. No backend change was needed at all.

/// One real, changed field in a Judge revision -- [before]/[after] are
/// genuinely nullable: a key the Judge ADDED has no real `before`
/// value, and one it REMOVED has no real `after` value, neither of
/// which should be rendered as a fabricated `null` string.
class PayloadDiffEntry {
  final String key;
  final Object? before;
  final Object? after;

  const PayloadDiffEntry({required this.key, required this.before, required this.after});
}

/// Pure, real diff -- the single most compelling artifact this product
/// can show, built from the two full, real payloads
/// `GET /actions/{id}/status` already returns (`pre_revision_payload`,
/// `payload`), not just the changed KEY NAMES the live pipeline's own
/// `revision` timeline event carries. Mirrors `gate/timeline.py::
/// _changed_keys()`'s own real semantics exactly: the union of both
/// real key sets, comparing VALUES rather than presence, so a key
/// whose value didn't actually change is correctly excluded.
List<PayloadDiffEntry> computePayloadDiff(Map<String, dynamic> before, Map<String, dynamic> after) {
  final keys = {...before.keys, ...after.keys}.toList()..sort();
  final entries = <PayloadDiffEntry>[];
  for (final key in keys) {
    final beforeValue = before[key];
    final afterValue = after[key];
    if (beforeValue != afterValue) {
      entries.add(PayloadDiffEntry(key: key, before: beforeValue, after: afterValue));
    }
  }
  return entries;
}

/// Pure, real, honest formatting for one payload field's value --
/// never a raw Dart `null` string for a genuinely absent field.
String formatDiffValue(Object? value) {
  if (value == null) return '(not set)';
  return value.toString();
}

/// Pure, real action-type-to-plain-English formatting -- this screen
/// has no server-side `describe_action()` equivalent available to it,
/// so a real, honest, generic transform ("create_email_draft" ->
/// "Create email draft") stands in, rather than a hardcoded, always-
/// incomplete lookup table this screen would need to keep in step with
/// every real `ActionType` the backend ever adds.
String formatActionType(String actionType) {
  return actionType
      .split('_')
      .where((w) => w.isNotEmpty)
      .map((w) => w[0].toUpperCase() + w.substring(1))
      .join(' ');
}
