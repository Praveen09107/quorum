# Quorum — Production-Grade Completion Plan

**Tier:** `tier1_foundation` · **Status:** Active, approved by Preethish (this document's own creation session) · **Companion to:** `QUORUM_IMPLEMENTATION_STRATEGY.md` (that document covers Phases 0–6 through the current live deployment; this one covers what comes after — the gap a full repository diagnosis found between "the specified sessions are done" and "this is a genuinely complete, autonomous, deployable product").

## Context

A full repository diagnosis found that Quorum's individual components are real, well-tested, and faithful to the finalized architecture — but the product has drifted from that architecture in aggregate: **nothing in this backend has ever autonomously triggered against real, live, changing user data.** The one negotiation that exists was inserted by a one-time manual script (`scripts/seed_demo_dataset.py`). All 5 domain agents' only real production caller is the `retry_queue` drainer, itself only reachable from that one hand-seeded negotiation. 5 of 13 real mobile screens (including a permanent bottom-nav tab, "Log") have no backend to connect to. There is no write/create UI anywhere in the app. Email and Calendar have no real data layer. The visual design is close to Flutter's stock Material 3. On-device LLM has never been confirmed working, for any model, ever. And re-reading `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` directly (not from memory) found 6 of its own §9.7 "newly built features" genuinely absent from this repository despite being described as complete — the same "specification narrative describes a different, no-longer-accessible environment" pattern `STATUS_INDEX.md`'s own intro paragraph already disclosed once (`DEC-050`), recurring in a document that was never reconciled the same way.

Root cause, stated plainly: every session's verification bar has been "is this component correct and tested in isolation," never "does the whole system now do something a real person can see or use." That is the actual mechanism of the drift this plan corrects, not any single wrong technical decision. `.claude/CLAUDE.md`'s new "Whole-system verification checkpoint" section exists specifically to make this structurally harder to repeat going forward — read it before starting any phase below.

This plan closes the gap directly: it builds the real autonomous loop before anything else (highest leverage, already possible with existing real domains), then closes each remaining domain/screen/execution gap in dependency order, then invests in visual design only once there's something real to design *for*, then hardens for production.

**Decisions confirmed with Preethish, binding for this plan:**
- Email and Calendar get built out fully — real Gmail/Calendar APIs, real sandbox account for anything that actually sends/books, not deferred.
- Sprint 0 (on-device LLM) gets retried for real, early, not accepted as permanently closed.
- The visual design gets a real, deliberate pass — custom type scale, spacing system, real componentry — sequenced after functional gaps close, not before.

**Cadence, matching the project's own established discipline:** one phase's sub-items proceed session-by-session, explicit approval between each (`CLAUDE.md`'s own binding cadence) — this plan sets direction and order, not a license to batch-run unsupervised. CRITICAL-tier fresh-context review (cross-model-equivalent per `DEC-005`'s established mechanism) on every session touching the Gate, secrets, auth, or a real external-action path — which is most of Phases 2–5. Every phase ends at a real whole-system checkpoint (`CLAUDE.md`) before the next begins.

---

## Phase 0 — Fix the process that let this happen ✅ RESOLVED, this document's own creation session

Added `.claude/CLAUDE.md`'s new "Whole-system verification checkpoint" section, this document, `STATUS_INDEX.md`'s new "Product Reality" section, and `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §9.7's own correction (6 of its 12 rows described files that do not exist in this repository — corrected in place, real design parameters preserved as valid guidance for the phases below that build them for real).

---

## Phase 1 — Sprint 0 retry (on-device LLM, real attempt)

**Goal:** get a real, final answer on whether an on-device model can actually load on this machine's real emulator, using the already-real harness — not repeat last time's untested assumption.

- Diagnose the real root cause precisely: the emulator's DNS relay failed to resolve `huggingface.co`. Try, in order: the emulator's proxy/DNS settings (`-dns-server` cold boot flag or AVD network config), a fresh cold boot of `quorum_sprint0`, and — if that's still broken — whether the real physical device (once reconnected) has working internet, since that's a cleaner real signal than fighting emulator networking.
- Re-run the existing, real `sprint0/` harness against both real candidates (Gemma 4 E4B, Llama 3.2 3B) for real this time.
- If a candidate genuinely loads: update `QUORUM_CONFIGURATION_CONSTANTS.md` §7 / `QUORUM_MASTER_REFERENCE.md` §5 with the real result. This unlocks two other real, currently-blocked pieces later in this plan: the Privacy Gate's real SLM classification call (`mobile/lib/privacy/privacy_gate.dart`'s already-tested-as-injected `slmClassifier`), and genuine on-device C0-complexity extraction for Phase 7's quick-capture flow.
- If it genuinely fails again for a different, real reason: that's a real, final, honest answer — document it precisely and close Sprint 0 for real, rather than leaving "DNS issue, never retried" as a live loose end for the rest of this plan.

**Verification:** the harness's own real, existing tests; a real screenshot/log of either a successful model load or a precise, new failure reason — never a repeat of last time's ambiguous outcome.

---

## Phase 2 — The autonomous trigger (highest leverage, uses only what's already real)

**✅ CLOSED AS FAR AS THIS PLAN CAN TAKE IT WITHOUT MORE SCOPE, `DEC-132`–`DEC-136`.** `pg_cron`/`pg_net` are genuinely enabled (turned out not to need Preethish's own dashboard action after all — a real, corrected assumption, `DEC-134`). `deadline-watch` and `spend-alert` (2 of the 4 named jobs) are real, tested, live, and scheduled (`*/30 * * * *`); `drain-retry-queue` is scheduled too (`*/5 * * * *`, `DEC-127`/`DEC-134`). A functionally-equivalent fourth job, `backfill-negotiation-detail` (not one of the plan's original four, but closing the real gap that made the two live jobs' own output actionable — a bare negotiation could never be resolved without it), is also real, live, and scheduled (`:12`/`:42`, `DEC-135`/`DEC-136`). All four confirmed firing unattended via real `200` responses, not just `cron.job_run_details`'s own weaker `'succeeded'`. `briefing` remains genuinely unspecified anywhere in this project's real corpus (confirmed directly against the ADD before deciding not to invent its shape) and `follow-up` remains genuinely blocked on Phase 4's Email `sent_messages` table — both correctly deferred, not silently dropped. A real, structural correction found while building deadline-watch: Career is not a first-class negotiation domain in the real schema (`Position.domain`/`ResourceClaim.claim_type` only ever resolve to `calendar`/`tasks`/`finance`) — see `DEC-132`. Two rounds of CRITICAL-tier review across this phase found and fixed 2 severe (permanent-silence-style) bugs each time — full detail: `STATUS_INDEX.md` item #30, `DECISIONS_LOG.md` `DEC-132`–`DEC-136`. **Honest limit:** the one real, live account's current data doesn't cross any trigger's threshold, so nothing has fired for a real reason yet — mechanically proven, not yet organically observed.

**Goal:** make Negotiation and the Gate genuinely autonomous for the 3 domains that are already real (Tasks, Finance, Career) — before touching Email/Calendar at all, because this doesn't need them.

- **Enable `pg_cron`/`pg_net` for real** on the live Supabase project (Preethish's own dashboard action — Database → Extensions) — the one item in this whole plan that needs Preethish directly; flag it first so it's not a late blocker. Then run `backend/scripts/enable_retry_queue_drain_cron.sql` (already written, `DEC-127`) for the drainer, and extend it with the new jobs below.
- Build the real scheduled jobs `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §13.4 already names ("briefing, deadline-watch, follow-up, spend-alert") — each a new `POST /internal/...` route, gated by the same real shared-secret pattern `main.py::_require_internal_secret` already established (`DEC-127`), each `pg_cron`-scheduled as a direct Cloud Run call, never a persistent worker:
  - **`deadline-watch`**: for each real user, runs `negotiation/trigger.py::scan_for_conflicts` against their real, current `tasks`/`expenses`/`applications` state — the first real, live, non-manual caller this function has ever had. A genuine conflict creates a real `negotiations` row exactly the way `scripts/seed_demo_dataset.py` did by hand, except now it happens on its own.
  - **`spend-alert`**: real budget-threshold monitoring over `expenses`, reusing `subscription_detective.py`'s already-real detection pattern for the recurring-charge signal.
  - **`briefing`**: composes the real `/today`-equivalent numbers server-side plus the weather enrichment `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §9.8 names (one free API call) — this is what eventually backs a real push notification/home-screen-widget refresh, not built this phase, but the real data-producing half is.
  - **`follow-up`**: stubbed this phase (needs Email's `sent_messages` table — built in Phase 4); wire the route now, leave its real logic for Phase 4 rather than inventing a fake interim version.
- Reuse `features/retry_queue_drainer.py`'s real patterns directly: `SELECT ... FOR UPDATE SKIP LOCKED` semantics for per-user iteration, the same transaction-boundary discipline this project's own review already fixed once (recovery logic outside the failed transaction — `DEC-128`), the same real-verified-then-hardened-anyway approach to any new numeric/data validation.

**Verification:** real, live-database tests seeding a genuine conflict (e.g., a real task deadline colliding with a real expense over budget) and asserting the real job creates a real `negotiations` row without any manual seed step; real CI; CRITICAL-tier review (this touches the Gate's real trigger path for the first time — Rule 6 territory). End-of-phase whole-system checkpoint: sign in on a real device/emulator, let a real cron interval pass, confirm a real negotiation appears in Today's "In motion" without anyone having run a script.

---

## Phase 3 — Google token storage (foundational for Email + Calendar-external)

**🔶 BACKEND + MOBILE CODE COMPLETE, `DEC-137` -- CRITICAL-tier review pending before merge, real live consent-flow verification still genuinely open.** Real, encrypted-at-rest storage (`auth/google_token_store.py`, migration `0010`), a real, separate refresh flow (`auth/google_token_refresh.py`), real revocation wired into account deletion with a real, deliberate reordering of that already-reviewed flow, and the mobile app's own real, incremental scope request (Gmail read/send/modify, Calendar events, `access_type=offline`, forced consent). **Honest limit, disclosed rather than assumed away:** no real, live, human-completed mobile consent flow with these new scopes has happened yet — whether Google's real, live authorization endpoint grants them to this project's real OAuth client without further Google Cloud Console configuration is genuinely unverified. Full detail: `DECISIONS_LOG.md` `DEC-137`.

**Goal:** close the real, disclosed gap `auth/google_oauth.py`'s own docstring already names — Google's `access_token`/`refresh_token` are deliberately never persisted today, which blocks any later, independent API call.

- New, real, encrypted-at-rest storage for a user's Google `access_token`/`refresh_token` (a new table or columns; real encryption via Postgres `pgcrypto` or application-level, keyed off a real secret in config — **CRITICAL tier, secrets handling, Rule 6**).
- A real Google-token refresh flow, genuinely separate from Quorum's own internal JWT refresh (`auth/refresh_token.py`) — do not conflate the two real, distinct token families the way `DEC-113` had to explicitly un-conflate `google_sub` vs. internal `user_id`.
- Real, incremental OAuth scope expansion — request `gmail.readonly`, `gmail.send`, `gmail.modify` (for archive/label), and `calendar.events` at consent time, disclosed clearly to Preethish before wiring, since this changes what the real consent screen asks a real user to grant.
- `security/supabase_deletion_store.py`'s own `revoke_oauth_tokens()` (currently an honest, disclosed zero) becomes real here too — an account deletion must now actually revoke the real Google tokens it stores, not just document why it doesn't.

**Verification:** real, live token-storage round-trip tests against the real database; a real, live refresh-token exchange against Google's real endpoint (sandbox account); CRITICAL-tier review, cross-model-equivalent given this is secrets handling.

---

## Phase 4 — Real Email domain (ingestion + execution)

**Goal:** Email actually becomes a real domain, not just an `action_events` label — and this is what unlocks Career's own real detection, since Career "rides on Email" (`QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §9.5) with no independent detection path of its own.

- Real Gmail API polling, 5–15 minute cadence (§9.1's own specified interval) — a new scheduled job in the Phase 2 pattern, reading real new mail via the real, now-stored Google token, extracting structured signals (never trusting raw model output uncritically — same Gate discipline as everywhere else).
- New `sent_messages`-style table — closes the real, disclosed gap blocking Waiting On, and completes `follow-up`'s stubbed route from Phase 2.
- Build `features/waiting_on.py` for real (doesn't exist in this repo despite the ADD's claim) — the 4-day staleness threshold is already specified (`QUORUM_CONFIGURATION_CONSTANTS.md` §4), reuse it, don't reinvent it. Wire `fetchWaitingOn` in `main.dart` — closes one of the 5 dead mobile screens.
- Real `SEND_EMAIL` execution in `features/action_executor.py` — the first real domain beyond Tasks/Finance to genuinely execute, via Gmail's real `users.messages.send`, using Phase 3's stored token. `ARCHIVE_EMAIL`/`LABEL_EMAIL` execution follows the same real pattern.
- Career's own real detection (application/interview classification riding on this same ingestion) becomes possible here — recommend building it as its own follow-on once Email ingestion is proven live for a few real days, not stacking two genuinely new external-integration risks in one phase.

**Verification:** real, live Gmail API calls against a dedicated sandbox Google account (never Preethish's real Gmail — Rule 5), never mocked; real database tests for the new table and Waiting On; CRITICAL-tier review (a new real external-action execution path). Whole-system checkpoint: a real email sent to the sandbox inbox is genuinely detected within one real polling interval.

---

## Phase 5 — Real Calendar domain (on-device primary, narrow cloud slice)

**Goal:** build calendar the way `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §9.2 actually specifies it — **not** a second full server-side Google Calendar integration. Ground truth is on-device.

- **Mobile-side, on-device:** integrate the `device_calendar` Flutter package (zero OAuth) to read whatever's already synced to the phone. This is what finally backs a real `CalendarAdapter` for `gate/validators.py`'s `availability_check`/`temporal_fact_check` — both currently untestable against real ground truth for lack of exactly this.
- **Cloud slice, narrow:** Google Calendar API used only for `CREATE_CALENDAR_EVENT_EXTERNAL` — real execution in `action_executor.py`, using Phase 3's stored token, only for the one case that genuinely needs it (inviting a real external person).
- Build `features/meeting_load.py` for real (doesn't exist despite the ADD's claim) — parameters already specified (8-hour working day, 0.25 buffer fraction, 0.7 overload threshold), reuse them.
- Decide, concretely, whether a backend `calendar_events` table is needed at all for *local* events (CalendarProvider already owns that ground truth on-device) — likely only a thin, real record of externally-booked events for negotiation-impact bookkeeping, not a full mirror.

**Verification:** real widget/integration tests against a real emulator's calendar provider; real, live `CREATE_CALENDAR_EVENT_EXTERNAL` execution tested against the sandbox account's real calendar; CRITICAL-tier review for the external-booking path.

---

## Phase 6 — Close every remaining domain/screen gap

**Goal:** finish what Phases 2–5 didn't reach, closing the rest of the dead-end screens and unbuilt ADD features.

- Real `UPDATE_BUDGET` execution — needs a genuine, small budgets-ceiling concept (a new column/table), the real gap `action_executor.py`'s own docstring already names.
- Build `features/predictive_risk.py` for real (doesn't exist) — parameters already specified (≥0.5 historical correction rate, ±1 deadline tolerance).
- Build `features/career_digest.py` for real (doesn't exist) — the real Tavily integration is already decided (`DEC-004`) and just needs implementing against the real, current Tavily API.
- Build `features/honesty_log.py` for real (doesn't exist) — a real route + wiring `fetchHonestyFeed` closes the permanently-dead "Log" bottom-nav tab, arguably the single most visible fix in this entire plan.
- Wire real Memory Transparency (`security/memory_transparency.py` already exists) — needs a real route plus Preethish's own mem0 signup (external, disclosed, his action, not ours).
- Close Gate Reveal for real: real `findings`/`objections` persistence on `action_events` (or a companion table) plus a real route — the drainer (Phase 2 onward) is now actually producing real Gate verdicts worth revealing.

**Verification:** each module gets the same real-data-driven test discipline as every other feature module in this backend; standard-tier fresh-context review per module (none of these touch Gate/secrets/external-action paths directly). Whole-system checkpoint: every item in the You tab's "More" section and every bottom-nav tab does something real.

---

## Phase 7 — Give the app something to write, not just read

**Goal:** address the zero-write-UI finding without contradicting the project's own thesis (AI proposes, not manual CRUD forms).

- A real, minimal **quick-capture** flow: free-text input (a natural extension of the already-real, already-built `share_intent_handler.dart`/`pending_share_provider.dart` share-target plumbing) that feeds the real domain agents' own existing natural-language construction paths (`tasks_agent`'s NL creation, `email_agent`'s draft-from-intent) — real proposals that go through the real Gate, the same path everything else in this plan uses. This demonstrates the actual product thesis interactively, rather than adding a parallel manual-entry system the architecture was never designed around.
- Route this through Sprint 0's on-device model for C0-complexity extraction/routing where Phase 1 succeeded (§10.2's own specified boundary), falling back to cloud otherwise.

**Verification:** real widget tests plus a real, live end-to-end proposal created from real free text, reviewed by the real Gate, visible in Today.

---

## Phase 8 — Real visual design pass (last, deliberately)

**Goal:** now that every screen has something real behind it, invest in how it looks — redesigning empty/dead screens first would have been wasted work.

- A real typography pairing via Google Fonts, a considered color system beyond one seed color, a real spacing scale.
- Redesigned card/list componentry for Today/Trust/Tasks/Finance/Career Pipeline/Search, replacing the current stock `Card(ListTile(...))` pattern throughout.
- Real motion for state transitions (Gate verdict reveal, negotiation choice, capacity/budget updates).
- Re-verify every screen against real, current data — not the demo seed alone.

**Verification:** `flutter analyze`/`flutter test` clean; a real, deliberate visual review pass (screenshots, on a real device/emulator) before calling this done — the same "verify the real running thing, not just the code" discipline this whole plan exists to restore.

---

## Phase 9 — Production hardening

**Goal:** close the remaining, purely operational gaps.

- Credential rotation (`STATUS_INDEX.md` item #17) — a precise, step-by-step checklist per provider console, Preethish's own action.
- Full CI/CD pipeline (`QUORUM_IMPLEMENTATION_STRATEGY.md` Phase 6, still untouched) — real build→test→deploy automation, not just PR-gating CI.
- A final, full, real, whole-system verification pass: real device, real sign-in, every domain, every tab, the autonomous jobs observed actually firing on schedule over real elapsed time (also finally answers the long-open "does pg_cron prevent Supabase's inactivity pause" question, `STATUS_INDEX.md` item #4).

**Verification:** this phase's own deliverable *is* the verification — a real, dated, honest account of the whole system working end to end, written into `STATUS_INDEX.md` and `DECISIONS_LOG.md` the same way every other real milestone in this project has been.

---

*Read `.claude/CLAUDE.md`'s "Whole-system verification checkpoint" section before starting any phase above, and run that checkpoint before moving to the next phase.*
