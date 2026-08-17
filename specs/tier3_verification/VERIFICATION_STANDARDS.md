# QUORUM — Verification Standards

**Tier:** `tier3_verification` · **Volatility:** Stable policy — the same status as `TESTING_STRATEGY.md`. Where that document describes *how* this project tests things, this document describes *what counts as verified at all* — the epistemic standard underneath every "real" claim in every session document since `IMPL_01`.

**Purpose:** the developer behind Quorum is a beginner working in a "vibe coding" style, with no human backstop reviewing generated code. That fact is why this document exists as an explicit, named policy rather than an implicit habit — because in this project, the Gate and this verification discipline carry more real weight than they would in a traditionally reviewed codebase. False confidence here isn't a style problem; it's the actual risk this whole methodology is built to prevent.

---

## 1. Three real states a claim can be in — and a claim must say which one applies

**VERIFIED.** The code or test actually ran, in this environment, and the real output is shown in full — not summarized, not paraphrased, not recalled from an earlier turn. Every backend claim in this project is VERIFIED. `pytest backend/tests -q` has been run, live, in every single session that touched backend code, and its literal output — currently `156 passed` — is what's reported, not an assumption that it would still pass.

**STRUCTURALLY CORRECT.** The code is written correctly against a real, documented API, cross-checked directly against source where genuine ambiguity existed, but this environment cannot execute it. Every mobile file in this project carries this status, stated explicitly in its own header comment: `UNVERIFIED IN SANDBOX — no Dart SDK here`. This is the honest ceiling of what can be claimed for mobile code in this environment, and no session has ever claimed more than that ceiling allows.

**FLAGGED UNCERTAIN.** A genuine, named gap in knowledge — not glossed over, not guessed at with false confidence. `CardThemeData` vs. `CardTheme` (`MOBILE_01`). The exact field names on `device_calendar`'s `Result<T>` (`MOBILE_04`). Dart's exact `.5`-rounding tie-break behavior (`MOBILE_13`). Each of these was a real point where this project could have picked the more likely answer and moved on quietly. Instead, each is named directly in the affected file's own comments and in `STATUS_INDEX.md`'s open-items list, with a real, specific path to resolving it (`flutter analyze` on first real build; a real Dart compiler check).

**A claim that doesn't say which of these three applies is treated as unverified by default.** This is the actual, load-bearing rule — the default assumption is the more cautious one, not the more convenient one.

## 2. Never fabricate success — the single rule everything else exists to serve

This project never reports a test as passing without having run it in that exact session. It never reports a document as internally consistent without having re-viewed the whole file after editing it. It never reports a real backend module as unaffected by a mobile-only session without having actually run `ruff check backend` and `pytest backend/tests -q` to confirm it, in that same session — a check performed **every single mobile session in this project**, without exception, specifically to catch the case where a mobile-focused change accidentally touched something backend-side.

The clearest concrete instance of this rule in practice: `STATUS_INDEX.md` itself was found to have drifted — orphaned rows, a duplicated section, a document count stale by 30 — not because anyone claimed it was fine, but because the discipline of re-viewing the whole file before trusting a sequence of edits caught the drift directly. The file was rewritten, and the drift was disclosed in the file's own text, rather than silently corrected and left unmentioned.

## 3. Checking the real source beats recalling it from memory, every time, even the tenth time

This is the single most repeated pattern across every session in this project: **before building against a schema, an endpoint, or an existing file, grep or view the real source directly — never proceed from what a prior session "probably" established.** This is not a one-time habit exercised early and then relaxed. It found eight real endpoint or schema gaps across `MOBILE_05` through `MOBILE_16` (a real correction to this section itself — a prior version of this document claimed "nine... through `MOBILE_19`," an uncounted number caught during a later full audit; the real, direct count against `QUORUM_DATA_CONTRACTS.md`'s own ordinal labels is eight, and `MOBILE_17`/`MOBILE_19`'s findings are correctly excluded from this count below, not folded into it), two genuinely new missing backend modules (`trust_digest.py`, `memory_transparency.py`), a stale docstring making a false claim about the Gate's existence (`MOBILE_16`), and — in the very last mobile session — a significant, previously-unnoticed gap between "every screen is real" and "a person can actually reach any of them" (`MOBILE_21`/`MOBILE_22`).

The pattern held even when checking confirmed nothing was wrong: `MOBILE_14` found the `/search` contract already complete and said so plainly, rather than manufacturing a finding to match the pattern of every session before it. A verification discipline that only reports problems, never a clean check, isn't actually checking — it's performing the appearance of checking. This project reports both outcomes honestly.

## 4. Uncertainty gets a decision, not a shrug: build it, defer it, or flag it — and the decision is explained

Not every gap gets the same response, and the difference is itself a real judgment this project makes explicitly rather than by default:

- **Genuinely bounded work gets built, immediately, to full rigor.** `trust_digest.py` (`MOBILE_17`) and `memory_transparency.py` (`MOBILE_19`) — real, new backend modules, confirmed missing, built to the same standard as anything in the original 23-session backend plan, because the scope was honestly small enough to do properly in one session.
- **Genuinely substantial work gets named and deferred, not rushed.** Wiring the real Gate into `self_test_harness.py` (`MOBILE_16`) and composing every remaining screen into full app navigation (`MOBILE_22`'s own successor item) were both confirmed to require real, cross-cutting redesign — and both were left explicitly open rather than patched shallow just to claim the box checked.
- **Genuine compiler-level uncertainty gets flagged, never guessed.** The `.5`-rounding boundary. `CardThemeData`. Both real, both left open, both with a stated real path to resolution.

## 5. What "done" means for a session in this project

A session is done when: every test it claims to pass has actually run in that session, with output shown; every file it edited has been re-viewed after editing, not assumed correct from having written it carefully; every real gap found along the way is either fixed, or named as a real, tracked open item with enough detail that a future session can act on it without re-discovering it from scratch; and every number in `STATUS_INDEX.md` — document counts, test counts, session counts — has been recomputed and checked against the underlying facts, not carried forward from the previous session's report.

**"Written" is not "done." "Structurally correct" is not "verified." "I checked this earlier" is not "I checked this now."** Every one of those distinctions has mattered at least once, concretely, somewhere in this project's real history — which is the actual argument for writing them down here, rather than trusting them to remain implicit indefinitely.
