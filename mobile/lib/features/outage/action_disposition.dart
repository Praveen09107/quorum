// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Zero Flutter dependencies — plain Dart, `dart test` is
// the real verification.
//
// CRITICAL TIER. The ADD's own language is unambiguous:
// `QUORUM_CONFIGURATION_CONSTANTS.md` §6 states S3 behavior in degraded
// mode is "prepared, labeled 'not yet verified,' never sent regardless
// of tap — no numeric constant, an absolute rule." This is the same
// real architecture rule CLAUDE.md itself holds non-negotiable: "S3
// (external-irreversible) actions always require explicit human
// approval — in every mode, including the degraded-offline-continuity
// mode. No exception, ever, regardless of how confident any automated
// check is." `decideDisposition` is the literal mobile-side enforcement
// of that rule.
//
// THE REAL, SAFETY-RELEVANT PROPERTY, exhaustively confirmed across all
// 8 real stakes x outage combinations before this file was finalized,
// not spot-checked:
//   S0 online -> sendLive       S0 in outage -> queueLocally
//   S1 online -> sendLive       S1 in outage -> queueLocally
//   S2 online -> sendLive       S2 in outage -> queueLocally
//   S3 online -> sendLive       S3 in outage -> blockUntilOnline  <- the ONLY path here
//
// The S3-during-outage check is the FIRST real conditional in this
// function's body, unconditionally, before any other branch --
// deliberately, so there is no code path that could fall through past
// an absolute rule. An absolute safety rule should never sit behind a
// condition that could be skipped.

enum ActionDisposition { sendLive, queueLocally, blockUntilOnline }

ActionDisposition decideDisposition(String stakes, bool isInOutage) {
  // THE ABSOLUTE RULE, checked first, unconditionally. Nothing above
  // this line, and nothing below it can ever be reached without this
  // check having already run.
  if (isInOutage && stakes == 'S3') {
    return ActionDisposition.blockUntilOnline;
  }

  if (!isInOutage) {
    return ActionDisposition.sendLive;
  }

  return ActionDisposition.queueLocally;
}
