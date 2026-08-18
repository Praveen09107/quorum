// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written (confirmed directly on this machine, same as MOBILE_01).
// Structurally correct against plain Dart language features only — no
// Flutter/package API surface in this file at all.
//
// A real, checked-not-assumed dependency, confirmed directly before
// writing a single line here: QUORUM_CONFIGURATION_CONSTANTS.md §7 was
// re-read, not recalled — it still reads "pending Sprint 0 (§19 of the
// ADD, not yet resolved)". IMPL_00 is fully specified but needs a real
// Android device this environment doesn't have, so it hasn't run. This
// file could have picked a model — Gemma, say — and quietly treated it
// as decided. That would be a real, dishonest shortcut: presenting a
// guess as a resolved architectural fact, exactly the failure mode this
// project's whole discipline exists to prevent. Built instead to be
// correct regardless of which model eventually wins.

/// Every real on-device model identifier this project's architecture
/// names anywhere (ADD §11.1, §10.7) — `unresolved` is a genuine, real
/// member of this enum, not a null-hack. A Full-tier device's model
/// choice IS one of these values; the honest fact is which one is not
/// yet known.
enum OnDeviceModelId {
  unresolved,
  gemma4E4B,
  llama32_3B,
  smolLM2_1_7B,
}

/// THE one constant every later session touching the on-device model
/// must read from, never re-guess. Stays [OnDeviceModelId.unresolved]
/// until `IMPL_00` (Sprint 0) genuinely runs on a real Android device
/// (≥4GB RAM) and measures a real winner between Gemma 4 E4B and
/// Llama 3.2 3B (ADD §11.1) — only Sprint 0's real execution is allowed
/// to change this value. A later session changing it without a real
/// benchmark having actually run would be a real regression, not
/// progress, no matter how confident the guess.
const OnDeviceModelId resolvedFullTierModel = OnDeviceModelId.unresolved;

/// A real thing that WAS resolvable now, correctly separated from what
/// wasn't: the Light tier's fallback model was locked independently of
/// Sprint 0's open question — confirmed directly against
/// `QUORUM_MASTER_REFERENCE.md` §5 ("On-device fallback | SmolLM2-1.7B |
/// Locked") before writing this, not assumed from memory.
const String lightTierModelId = 'SmolLM2-1.7B';
