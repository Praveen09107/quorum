# Quorum — Final Completion Plan

**Tier:** `tier1_foundation` · **Status:** Active, approved by Preethish (this document's own creation session) · **Companion to:** `QUORUM_PRODUCTION_COMPLETION_PLAN.md` (Phases 0–9, substantially complete — see `STATUS_INDEX.md` for the real, current per-phase tally). This document is what comes after: the specific, remaining, real work needed to go from "substantially complete" to genuinely, fully complete — every deliberately-deferred scope decision reopened and closed, every domain fully realized, and a real, installable Play Store presence.

## How this plan was built

Not from memory, and not by trusting old checkmarks. Every claim about "what's already done" below was re-verified directly against real files in this repository during this same session — `agents/email_agent.py`, `calendar_agent.py`, `finance_agent.py` (confirmed: zero LLM calls in calendar/finance, `email_agent.py` has a real, injectable `LlmCall` type with zero real callers), `security/memory_transparency.py` (confirmed: schema/grouping logic only, no real `mem0` client, no route), the mobile `memory_transparency_screen.dart`/`you_screen.dart` (confirmed: the real UI and drill-through link already exist, only the backend + fetcher wiring are missing), `DECISIONS_LOG.md` DEC-159 (confirmed the *exact* real Secret Manager free-tier ceiling: 6 active secret versions/month, project-wide, and which 4 of 10 real secrets remain plain env vars, and why that's a correctly-accepted, budget-bound stopping point, not open work), and a live web check of Google's own current OAuth scope-verification policy (confirmed `gmail.readonly`/`gmail.modify` are classified **Restricted**, not Sensitive — the single most consequential fact this planning pass surfaced).

## Five decisions confirmed directly with Preethish, binding for this plan

1. **Every deliberately-deferred scope decision from the prior plan is reopened and completed** — Quick-capture's domain limitation (Tasks-only), on-device-first extraction routing, and Career's own Email-riding interview detection are all real, remaining work now, not settled exceptions. (The one exception, carved out separately below: the *architecture-level* Critic≠Judge provider split is a `CLAUDE.md` "must never be violated" fact, not a scope deferral — it stays exactly as it is.)
2. **"Production-ready" means:** code/infrastructure genuinely production-grade and fully verified end-to-end (the existing bar), **plus** a real, installable Google Play Store presence. Explicitly **not** required: a real monitoring/alerting stack beyond the existing Langfuse tracing, or legal/ToS documentation beyond what Play Store itself requires.
3. **AI provider rebalancing:** shift real `generateContent` load off Gemini's shared, scarce free-tier quota (20 requests/day, confirmed live, `DEC-165`) onto Groq wherever `CLAUDE.md`'s own protected architecture fact allows it. **The Judge stays on Gemini, the Critic stays on Groq — this specific pairing is explicitly protected and this plan never touches it.** Every *other* real `generateContent` call site (negotiation position/synthesis, quick-capture extraction, downstream translation, career digest summarization) moves to Groq.
4. **Owner-only real actions** (a `mem0.ai` signup, credential rotation, a Google Play Developer account) are scheduled as explicit, dated steps inline in this plan, gating only the specific work that genuinely needs them — never a disconnected side list.
5. **Play Store submission targets the Closed Testing track, with the Google OAuth consent screen kept in "Testing" publishing status.** This was a real, load-bearing correction found during this planning pass, not assumed: Quorum's real Gmail scopes (`gmail.readonly`, `gmail.modify`) are classified **Restricted** by Google, which requires a paid, recurring CASA Tier 2 third-party security assessment ($540–$1,800/year, 4–12+ week review, annual recertification) before an app can leave "Testing" status — a real, direct conflict with this project's own explicit, standing "free-tier only" constraint. Staying in Testing/Closed-Testing avoids this entirely, for free, while keeping every real Gmail/Calendar feature fully intact — the correct choice for a portfolio project with no real public user base. **Confirmed live, not assumed** (Google's own current developer documentation, checked directly during this session): [Restricted scope verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification), [Sensitive scope verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/sensitive-scope-verification).

## What this plan deliberately does NOT reopen

- **The Critic (Groq) / Judge (Gemini) model-provider split** — a `CLAUDE.md` "must never be violated" architecture fact, not a scope decision. Decision 3 above rebalances *everything else*, never this pairing.
- **Migrating the remaining 4 plain-env-var secrets** (`GROQ_API_KEY`, `TAVILY_API_KEY`, `UPSTASH_REDIS_REST_TOKEN`, `LANGFUSE_SECRET_KEY`) to Secret Manager — real, live-confirmed impossible within the real, free-tier 6-secret ceiling (`DEC-159`) without incurring an explicitly-forbidden real cost. Already correctly disclosed and accepted as a standing, budget-bound limit, not new work this plan should reopen.
- **A real server-side `CalendarAdapter`** (pushing on-device calendar contents to the cloud) — this was framed in the codebase itself as a genuine **privacy** decision, not a scope-narrowing-for-time decision (`DEC-152`'s own disclosed non-build reasoning). Decision 1 above reopens *scope* deferrals; it does not override a privacy boundary nobody has actually revisited. If Preethish wants this reopened too, it needs its own explicit decision — flagged here as a real, disclosed open question, not silently included or silently dropped.

---

## The optimal implementation order, and why

Twelve real sessions, in this specific order — not the order the gaps happen to be listed in. The reasoning:

- **Sessions 1–3 are foundational and de-risking, done first on purpose.** The Groq migration (Session 1) doesn't just rebalance load — it's what actually makes Session 2 (finally witnessing the two built-but-never-seen animations) possible today rather than "whenever Gemini's quota happens to allow it," and it's what every one of Sessions 4–8's *new* AI call sites should be built against from the start, so none of that work has to be built once and then migrated later.
- **Sessions 4–8 (the Quick-capture domain expansion) are sequenced by real risk, not alphabetically:** Finance and Calendar first (closest to the already-proven Tasks pattern, lowest novel risk), then Edit/Modify (needs genuinely new Gate schema — the new `ActionType`s and stakes classifications should exist before Email, the highest-stakes domain, is built against them), then Email last (real, external, S3-adjacent consequences — the domain where getting the pattern right *before* building it matters most), then on-device routing last within this cluster (a real optimization layer added only once every domain's cloud path is already proven correct).
- **Session 9 (push notifications) and Session 10 (Memory Transparency) are genuinely independent of the Quick-capture cluster** and could run in parallel with it if Preethish wants — they're sequenced after it here only because Quick-capture is the higher-value, thesis-central work.
- **Session 11 (final whole-system verification) has to be last among the engineering sessions** — it's only meaningful once every domain is actually done, not a partial check repeated after every session.
- **Session 12 (Play Store) is genuinely last** — packaging and shipping work that would otherwise need repeating if done before the feature set stabilizes.
- **Owner-only actions are pulled forward wherever they don't block anything**, so they're never a late surprise: the `mem0.ai` signup and credential rotation can both start today, in parallel with Session 1, since neither blocks any engineering work until the specific session that needs them.

---

## Session 1 — AI provider rebalancing + Cloud Run runtime identity hardening

**What:** Move four of this backend's five real `generateContent` call sites off Gemini onto Groq: `negotiation/gemini_calls.py` (position + synthesis calls), `features/quick_capture.py` (task extraction), `negotiation/downstream_translation.py`, `features/career_digest.py` (summarization). The Judge (`gate/llm_calls.py`) stays on Gemini — untouched. In the same session, replace the Cloud Run **runtime** service account (`649581407643-compute@developer.gserviceaccount.com`, still holding project-wide `roles/editor` per the real, standing, disclosed gap from `DEC-159`/`DEC-162`) with a new, narrowly-scoped runtime identity holding only `roles/secretmanager.secretAccessor` on the 6 real secrets it actually reads.

**Why:** The Gemini 20/day ceiling is shared across every one of these five real features with zero coordination beyond `DEC-165`'s own quota guard — moving four of them to Groq (whose own real, already-proven headroom is far higher, confirmed by this project's own Critic already running there) doesn't just relieve pressure, it removes an entire class of real failures this session's own earlier work spent hours diagnosing and fixing around. The Cloud Run runtime identity fix closes the one remaining real, disclosed security gap from `DEC-159`'s own CRITICAL-tier review — deliberately deferred twice already ("a real candidate for a future session run with Preethish available"), and this is that session.

**Depends on:** Nothing. This is the first, foundational session precisely because nothing else does either.

**How:**
1. For each of the four call sites, replace the real Gemini `generateContent` HTTP call with a real Groq `chat/completions` call using `gate/llm_calls.py`'s own already-proven `GROQ_CRITIC_MODEL = "openai/gpt-oss-120b"` and its own real, live-confirmed `json_schema` structured-output configuration as the direct template — this project has already solved "does Groq's own structured JSON output work for this exact class of problem" once; reuse that solution, don't re-derive it.
2. Each call site's own real JSON schema (position/severity/resolution; task title/hours/deadline; finance/tasks/calendar translation shapes; digest summary points) needs its own real, live verification that Groq's `json_schema` mode actually enforces it correctly — do not assume it generalizes from the Critic's own, differently-shaped schema without checking.
3. `core/gemini_quota.py`'s own guard stays wired to the Judge only, since it's now the only real remaining Gemini `generateContent` caller — the other four call sites simply no longer need it (they'll want their own, much more generous real Groq rate-limit awareness instead, matching `gate/llm_calls.py`'s own existing `_call_groq_json` retry pattern).
4. For the runtime identity: create a new real service account, grant it `roles/secretmanager.secretAccessor` on exactly the 6 real secrets (mirroring `DEC-159`'s own per-secret, least-privilege grant style — never a project-wide role), redeploy Cloud Run with `--service-account=<new-sa>`, and confirm the live service still starts cleanly and serves real traffic under the new, narrow identity before revoking the old default's own broad grants.

**What must be true before moving on:** every one of the four migrated call sites has a real, live, passing test proving Groq returns correctly-shaped output for that exact real schema; the Judge is confirmed still running on Gemini and nothing else touches it; the live Cloud Run service is confirmed serving real traffic under the new, narrow runtime identity, with the old default compute SA's own broad grants revoked (not just unused — actually revoked, closing the gap for real).

**Verification:** `ruff check backend` clean; the full real backend suite passing with the newly-migrated call sites exercised live (not mocked) against the real Groq API; a real, live `GET /health` returning `200` under the new runtime identity; CRITICAL-tier cross-model review (this touches the Gate-adjacent negotiation/quick-capture/career-digest paths, all previously reviewed at this tier, plus real IAM/security changes).

**Expected result:** Gemini's real, shared daily quota is now spent almost entirely on Judge calls alone — freeing real, meaningful headroom for every feature built in Sessions 4–8. The live backend runs under a real, narrowly-scoped identity with no more project-wide `roles/editor` anywhere in its serving path.

---

## Session 2 — Witness the two flagship animations, for real

**What:** Generate real, Gemini-backed (Judge) / now-Groq-backed (position/synthesis) negotiation detail for the existing bare "Finance vs. Tasks" negotiation (`scripts/seed_demo_dataset.py --with-negotiation-detail`), and confirm on the real device that both of Phase 8's built-but-never-witnessed animations — the Gate Reveal Stage A→B staged reveal, and the negotiation-choice cross-fade — actually render correctly.

**Why:** These are real, shipped, tested pieces of this app's own visual thesis that no human has ever actually seen work. Session 1 is precisely what makes this achievable today rather than "whenever Gemini's quota happens to reset."

**Depends on:** Session 1 (the position/synthesis calls this needs are now on Groq, not competing with the Judge for the same scarce real slots).

**How:** Run the real seed script's `--with-negotiation-detail` mode; if it succeeds, reconnect the real device, tap into the now-detailed "Finance vs. Tasks" negotiation and confirm the real cross-fade; separately, either wait for a real S2/S3 action to naturally acquire real, persisted `findings`/`objections` (the Gate Reveal screen's own real data source since `DEC-146`), or construct one deliberately (e.g. a real, fresh Quick-capture task landing on a genuine Stage-A deadline conflict) to produce a real Gate Reveal-eligible action, then tap into it on the real device.

**What must be true before moving on:** both animations have been directly, visually confirmed on the real device — not "the code looks right," an actual human has watched them run.

**Verification:** real, dated screenshots or a direct on-device confirmation, written into `STATUS_INDEX.md`'s Product Reality section the same way every other real on-device milestone in this project has been.

**Expected result:** every piece of Phase 8's real visual/motion system has now actually been seen working, closing the single standing gap the last whole-system checkpoint named.

---

## Session 3 — Career's real Email-riding interview detection

**What:** Build the real, autonomous classification step Phase 4's own text explicitly deferred: scanning newly-ingested real emails (`features/email_ingestion.py`, real and live since `DEC-140`) for genuine interview-related signal, cross-referencing against a user's real `applications` rows, and updating `applications.status` to `interview_scheduled` when a real match is found — closing the one Phase 4 item never picked back up.

**Why:** This is the last remaining named item from Phase 4, deliberately deferred ("recommend building it as its own follow-on once Email ingestion is proven live for a few real days") — Email ingestion has now been live for weeks, the real waiting period this text asked for has already passed.

**Depends on:** Session 1 (this is a new, real classification call — build it directly on Groq, matching Decision 3, never introduce a fifth new Gemini call site).

**How:** A new function in `features/email_ingestion.py` (or a small, new, adjacent module if the existing file's own scope discipline argues for separation — check its own top-of-file docstring first, matching this project's own "read before extending" discipline) that, for each newly-ingested real email, makes one real Groq call asking a narrow, structured question ("does this email's real subject/body genuinely indicate a real interview has been scheduled, and if so, for which real company") against the user's own real, currently-open `applications` rows as context — never a broad, unscoped classification. On a genuine match, update `applications.status` directly, matching the exact same real transition `career_digest.py`'s own autonomous trigger already watches for (`applications.status = 'interview_scheduled'`), so this session's new detector becomes a real, second, independent trigger feeding directly into already-real, already-live downstream capability, not a dead end.

**What must be true before moving on:** a real, live end-to-end test — a genuine interview-confirmation-shaped email ingested for a real, seeded application, confirmed to genuinely flip that application's real status, confirmed to genuinely trigger `career_digest.py`'s own already-real autonomous digest compilation afterward.

**Verification:** real, live-database integration tests (never a fabricated classification result); CRITICAL-tier review (this is a new autonomous trigger writing to real user data, matching the same tier every other trigger job in this backend already received).

**Expected result:** Career's own real detection pipeline is now fully autonomous end to end — a real interview email arrives, the application's status updates itself, and a real digest compiles, with no manual step anywhere in that chain.

---

## Session 4 — Quick-capture → Finance domain

**What:** Extend Quick-capture's real free-text-to-Gate pipeline to Finance: real free text like "spent 800 on groceries" or "raise my monthly budget to 60000" becomes a real `LOG_EXPENSE`/`UPDATE_BUDGET` proposal, through the same real Gate review every other Quick-capture proposal already uses.

**Why:** This is the first of the three real domains Quick-capture's own launch deliberately deferred (`DEC-153`: "Tasks was chosen instead... on-device extraction/routing is a real, disclosed, deferred follow-on"), reopened per Decision 1. Finance is the lowest-risk of the three remaining domains — `finance_agent.py`'s own `build_finance_proposal()` already exists and needs no changes, confirmed directly this session.

**Depends on:** Session 1 (the new extraction call is built directly on Groq).

**How:** A new, real Groq-backed extraction call (matching `quick_capture.py`'s own existing tasks-extraction prompt structure exactly, including its own real, explicit prompt-injection framing) that classifies real free text into one of `finance_agent.py`'s own real `FinanceAction` values (`log_expense`/`update_budget`) plus the real structured fields each needs (`amount`, `category`, `payee` for expenses; `amount`, `category` for a budget change). Reuse `finance_agent.py::build_finance_proposal()` directly, unmodified, exactly the way `quick_capture.py` already reuses `retry_queue_drainer.py`'s own real, shared Stage-A-construction helpers rather than re-deriving them.

**What must be true before moving on:** a real, live, end-to-end test — real free text genuinely produces a real `expenses` row (or a real `users.monthly_budget_limit` change) through the real Gate, with the same real deadline/budget Stage-A checks every other finance-domain path already gets.

**Verification:** real, live-database integration tests plus a real capstone test against the real Groq API (never skipped, matching this project's own established discipline for exactly this class of test); CRITICAL-tier review (a new real Gate-invoking, execution-invoking path).

**Expected result:** the FAB's own free-text flow now genuinely covers two real domains, not one.

---

## Session 5 — Quick-capture → Calendar domain

**What:** Extend Quick-capture to Calendar: real free text like "block 2pm-3pm tomorrow for a design review" or "set up a call with jane@company.com next Tuesday at 10" becomes a real `CREATE_CALENDAR_EVENT_LOCAL`/`CREATE_CALENDAR_EVENT_EXTERNAL` proposal.

**Why:** The second of the three deferred domains. `calendar_agent.py`'s own `build_event_proposal()` already exists (confirmed this session — it needs no changes), and its own real, load-bearing `has_external_invitee`/`invitee_email` distinction (a real, disclosed `DEC-151` fix) already correctly separates the two real stakes levels.

**Depends on:** Session 1 (Groq); benefits from Session 4 existing first as a second, real, working reference for "how a new Quick-capture domain gets wired," but has no hard technical dependency on it.

**How:** A new, real Groq-backed extraction call producing `proposed_start`/`proposed_end`/`title`/`has_external_invitee`/`invitee_email` (`None` whenever the real free text names no real external person — never fabricated, matching `calendar_agent.py`'s own existing, real "never guessed" discipline for this exact field). Needs a real, explicit time-anchor in the prompt (the current real UTC timestamp, matching the fix `DEC-153`'s own review already found necessary for "due next Friday"-style relative dates) so relative real phrasing resolves correctly. Reuse `build_event_proposal()` directly.

**What must be true before moving on:** a real, live, end-to-end test for both the local and external-invitee real paths, including a real, live Google Calendar booking for the external case (sandbox account, matching Rule 5's own carve-out for anything that actually touches a real external destination).

**Verification:** real, live-database tests; a real, live Google Calendar API round-trip for the external path (create → get → delete, matching `DEC-151`'s own established verification pattern exactly); CRITICAL-tier review.

**Expected result:** three of five real domains now reachable from the one, unified free-text entry point.

---

## Session 6 — Quick-capture → Edit / Modify flow

**What:** A real way to modify or remove an existing task, expense, application, or local event via the same free-text, Gate-reviewed flow — e.g., "push the Q3 budget review deadline to Friday" or "mark the Notion application as rejected" — genuinely closing the "cannot currently edit or delete anything" gap without contradicting the project's own stated thesis (AI proposes, Gate reviews — never a manual CRUD form).

**Why:** This is real, disclosed, currently-open work (`STATUS_INDEX.md`'s own "Cannot currently do" list), and building it as a natural-language, Gate-reviewed flow — rather than a parallel manual-edit UI the architecture was never designed around — is the only implementation that's actually consistent with Phase 7's own founding goal text.

**Depends on:** Sessions 4–5 (this reuses the same real extraction infrastructure both just established, and needs Finance/Calendar's own real proposal-construction functions already wired for the "modify" case to have something concrete to modify).

**How:** This is real, new Gate-adjacent architecture, not just a new prompt — plan for it accordingly:
1. `gate/schemas.py`'s real `ActionType` enum already defines `UPDATE_TASK`/`UPDATE_APPLICATION_STATUS` with zero real callers (confirmed by `action_executor.py`'s own docstring) — these become real for the first time here. New real types are needed for expense modification and for deletion across every domain (`UPDATE_EXPENSE`, `DELETE_TASK`, `DELETE_EXPENSE`, `CANCEL_CALENDAR_EVENT_LOCAL`, etc.) — enumerate the real, closed set needed, don't invent more than the four domains actually require.
2. `router.py`'s own hardcoded `STAKES_TABLE` needs a real, deliberate stakes assignment for each new type — a deletion is a meaningfully different real stakes level from a field edit, and this needs the same explicit, reasoned classification every existing entry already has, never inferred.
3. A new extraction call classifies real free text into "which domain, which existing real record, create/modify/delete, what changes" — this is genuinely the most ambiguous of the five real extraction tasks (resolving *which* existing task/expense/application a vague reference like "the Q3 one" means), and needs real, live testing against real, deliberately ambiguous inputs before trusting it, not just the clean, unambiguous cases.
4. `action_executor.py` gains real execution branches for each new type, following its own already-established pattern (real row-count verification after every write, matching its own `DEC-148` precedent) exactly.
5. Mobile: a real "Edit"/"Delete" affordance on each existing task/expense/application detail view that opens the same Quick-capture screen, pre-filled with real context (which record, its real current values) rather than a bare blank field — genuinely helping a real person phrase an edit precisely, not just technically permitting one.

**What must be true before moving on:** a real, live end-to-end test for every new `ActionType`, including at least one deliberately ambiguous real free-text input confirmed to either resolve correctly or fail loud (never silently guess wrong and modify the wrong real record) — this is a Gate-adjacent write path touching real user data destructively; ambiguity-handling correctness matters more here than in any other Quick-capture domain.

**Verification:** real, live-database tests including a dedicated cross-user-isolation proof (a modify/delete request must never be able to reach a different real user's row); CRITICAL-tier review, explicitly probing the ambiguous-reference-resolution logic adversarially (a real reviewer should try to get it to modify the wrong record).

**Expected result:** the app can now genuinely edit and delete real data across every domain, entirely through the same real, Gate-reviewed thesis every other write path already uses.

---

## Session 7 — Quick-capture → Email domain

**What:** Real free text like "tell Sarah the proposal looks good, I'll send the contract Monday" becomes a real, Gate-reviewed `SEND_EMAIL` draft-and-send proposal, using `email_agent.py`'s own real, already-existing `draft_reply_node`/`build_reply_proposal` — the one real agent in this backend that already has a genuine, injectable LLM-call type with zero real callers, confirmed this session.

**Why:** The third and highest-stakes of the three deferred domains — sequenced last within this cluster deliberately, once the extraction/Gate-wiring pattern has been proven three times over on lower-consequence domains first.

**Depends on:** Sessions 4–6 (the established pattern) and Session 6 specifically resolves a real, structural question this domain also needs: how a real recipient gets resolved from ambiguous free text (e.g., "tell Sarah" — matching against a real prior thread/contact, the same "resolve which existing real thing this refers to" problem Session 6 already had to solve for edits).

**How:** `email_agent.py`'s own docstring is explicit that this agent "still needs a real `recipient` supplied separately (never extracted from the text)" — this session builds the real recipient-resolution step that's been genuinely missing since `DEC-153` first found this gap: match the free text's own named person against real prior `sent_messages`/thread data (`waiting_on.py`'s own real table) to resolve a real email address, and fail loud — never guess — when no confident real match exists. The extraction call itself (on Groq) produces the real draft intent/tone; `email_agent.py`'s existing `draft_reply_node` handles the actual drafting call.

**What must be true before moving on:** a real, live, end-to-end test sending a genuine email to the real sandbox account through this exact path, plus a real, deliberate test of the "no confident recipient match" case failing loud rather than guessing.

**Verification:** real, live Gmail API send (sandbox account, Rule 5); CRITICAL-tier review (a real S3, human-approval-gated send path — the highest-stakes single action type in this entire system).

**Expected result:** all five real domains are now reachable from the one, unified, Gate-reviewed free-text entry point — Quick-capture's own founding thesis, finally realized in full.

---

## Session 8 — On-device-first extraction routing

**What:** Route every one of the five Quick-capture domains' own extraction call through Sprint 0's real, winning on-device model (Llama 3.2 3B, `DEC-130`/`131`) first, for genuinely C0-complexity intents, falling back to the real cloud path (Groq) whenever the on-device result is missing, malformed, or below a real, deliberately-conservative confidence bar.

**Why:** The last of the three original Quick-capture deferrals (`DEC-153`: "Sprint 0's own real, measured result is 67% validity for the winning on-device candidate — not yet strong enough to be the primary path for something that writes real data... on-device extraction/routing is a real, disclosed, deferred follow-on, not silently dropped"). Sequenced last within this cluster on purpose: prove every domain's cloud path correct first, then add the on-device fast-path as a genuine optimization layer on top of an already-proven baseline, never the only path.

**Depends on:** Sessions 4–7 (every domain's real cloud extraction call must exist and be proven correct before this session can safely add a fallback path in front of it).

**How:** A real, on-device classification pass (matching §10.2's own specified C0-complexity boundary — extraction/routing only, never drafting or negotiation) attempts each of the five domains' own extraction shape locally first; a real, concrete, disclosed correctness bar (not simply "did it produce valid JSON," but a real, structural sanity check per domain — e.g., a parsed date that's genuinely in the future, an amount that's genuinely a positive real number) decides whether to trust the on-device result or fall back to the real cloud path. Every fallback is logged, not silent, so the real on-device/cloud split ratio is honestly observable afterward.

**What must be true before moving on:** a real, live comparison across a real, deliberately-varied sample of free-text inputs per domain, showing the on-device path's own real, measured accuracy and fallback rate — not assumed from the original 67% figure (measured on a different, narrower task), re-measured for real against this specific, now much richer set of five extraction shapes.

**Verification:** real, live on-device inference tests on the real device; a real, honest report of the measured on-device-vs-cloud split and accuracy, written into `STATUS_INDEX.md`.

**Expected result:** Quick-capture now genuinely tries the on-device model first wherever it's trustworthy enough to, cutting real cloud dependency for the simplest, most common real intents, with cloud as a real, honest, always-available fallback — never a silent regression in correctness for the sake of using the on-device path.

---

## Session 9 — Real push notifications for `briefing`

**What:** The real consumer `features/briefing.py`'s own docstring named as "not built this phase" — a real Firebase Cloud Messaging (FCM, genuinely free-tier) integration that turns `briefing`'s already-real, already-composed per-user data into an actual real push notification delivered to the real device.

**Why:** `briefing` (`DEC-163`) is real, tested, and genuinely inert today — it computes correct data for no one. This is the one piece standing between "a real backend job that runs" and "something a real, signed-in user actually experiences," the exact axis this project's own whole-system-checkpoint discipline exists to track.

**Depends on:** Nothing from Sessions 1–8 — genuinely independent, sequenced here for value-ordering reasons only.

**How:** Backend: a new, real, small table storing each real user's current FCM device token (registered on real app launch/sign-in), and a real call to Firebase's own Admin SDK (or its real REST API, matching this project's own "direct REST call over vendor SDK" convention established for Gemini/Groq/Tavily/Upstash) inside `briefing`'s own existing composition function, sending a real, concise notification once real data is composed. Mobile: real FCM SDK integration, a real, explicit notification-permission request (Android 13+ requires this explicitly), and a real deep-link from a tapped notification straight into Today.

**What must be true before moving on:** a real, live push notification genuinely received and displayed on the real device, tapped, and confirmed to land on Today — not a simulated/logged send.

**Verification:** a real, live, on-device test of the full round trip; standard-tier fresh-context review (no Gate/secrets/external-irreversible-action path — a notification is not itself an irreversible action).

**Expected result:** `briefing` stops being inert — a real, signed-in user now genuinely receives a real daily summary on their real device without opening the app first.

---

## Session 10 — Memory Transparency (`mem0`)

**Preethish's own real action, scheduled now, gating this session specifically (start today — it doesn't block anything else in this plan):** sign up for a real `mem0.ai` account and generate a real API key. Nothing else in this plan needs this; only this session does.

**What:** Wire the real, live `mem0` API into this backend for the first time — a real client, real `GET /memories`/`DELETE /memories/{memory_id}` routes, and the real mobile fetcher injection `main.dart` is already structured to receive (the screen and its own drill-through link from You already exist, confirmed this session — only the data layer is missing).

**Why:** The one remaining item from Phase 6, blocked the whole time on exactly one real, external, owner-only action.

**Depends on:** Preethish's own real `mem0.ai` signup (see above). Nothing else.

**How:** A new `core/mem0_client.py` (matching this project's own "direct, minimal REST wrapper, not a vendor SDK" convention) implementing real `list_memories`/`delete_memory` calls against `mem0`'s own real API, using `security/memory_transparency.py`'s already-real `Memory` dataclass and `group_by_category()` as the shape every real response gets parsed into. New `GET /memories`/`DELETE /memories/{id}` routes in `main.py`, real per-user auth. Mobile: a new `api/memory_transparency_api.dart` (matching every other real fetcher's established shape) wired into `main.dart`'s existing `MainShell` construction — the screen itself needs no changes.

**What must be true before moving on:** a real, live round trip — a real memory genuinely stored via whatever real path already writes to `mem0` (confirmed first: which real, existing code path, if any, currently writes memories at all — `gate/validators.py`'s own calendar-buffer-preference read implies *something* writes them; confirm this directly before assuming a write path already exists, and build one if it genuinely doesn't), listed correctly through the new route, and genuinely deleted.

**Verification:** a real, live integration test against the real `mem0` API (Rule 5); standard-tier review.

**Expected result:** the last dead mobile-adjacent surface in this app becomes real — a signed-in user can see and delete their own real, stored memories for the first time.

---

## Session 11 — Final, full, whole-system verification pass

**What:** The real closer Phase 9's own text always named but couldn't yet mean in full: a real device, real sign-in, every one of the now-five real Quick-capture domains, every autonomous job observed firing on its own real schedule, Memory Transparency, real push notifications — the entire, now-fully-realized system, exercised end to end by an actual human.

**Why:** Every individual session above gets its own real verification; this is the whole-system check that catches what only shows up in combination — exactly the discipline `CLAUDE.md`'s own "Whole-system verification checkpoint" section exists to enforce, now meaningful in a way it couldn't be until every domain was actually real.

**Depends on:** Sessions 1–10, all of them.

**How:** `ruff check backend` + the full real backend suite; `flutter analyze` + `flutter test`; a real, live hit against the deployed Cloud Run backend; then, on the real device: sign in, create a real proposal in each of the five domains via Quick-capture, edit and delete something, confirm a real push notification arrives, confirm Memory Transparency lists and deletes a real entry, confirm the two flagship animations still work, and let real elapsed time pass to reconfirm the autonomous jobs are still firing cleanly.

**What must be true before moving on:** every one of the above is genuinely, individually confirmed working on the real device — not inferred from passing tests.

**Verification:** this session's own deliverable *is* the verification — a real, dated, honest account written into `STATUS_INDEX.md`'s Product Reality section, rewritten (not appended to) the same way every other real milestone in this project has been.

**Expected result:** a real, current, honest, complete answer to "what can a real, signed-in user see and do, end to end, right now" — and for the first time, that answer is "everything this project ever set out to build."

---

## Session 12 — Play Store packaging and Closed Testing submission

**What:** A real, installable Play Store presence via the Closed Testing track, with the Google OAuth consent screen deliberately kept in "Testing" publishing status (Decision 5 above) — never full public production.

**Preethish's own real actions, scheduled explicitly:**
1. **Register a real Google Play Developer account** — a real, one-time $25 fee.
2. **Generate a real Play App Signing key** through Play Console's own now-standard flow.
3. **Add up to 100 real, explicit test-user emails** to the Google Cloud OAuth consent screen's own Testing allowlist (the real, free mechanism that keeps this app permanently exempt from the Restricted-scope CASA requirement) and the same real people as Play Console Closed Testing testers.

**Why:** The real, final piece of Decision 2's "production-ready" definition — a genuine, installable, professionally-packaged presence for portfolio purposes, achieved without incurring the real, recurring CASA cost Decision 5 correctly ruled out.

**Depends on:** Session 11 (submit only once the feature set is genuinely stable — resubmitting store assets after every subsequent change is real, avoidable overhead).

**How:** Real app icon and Play Store listing assets (screenshots, a short real description); a real, hosted privacy policy page (required even for Closed Testing — a simple, real, static page describing exactly what this app's real Gmail/Calendar/Finance/Task data access does and doesn't do, hosted anywhere real and stable); Play Console's own real Data Safety form, filled out accurately against what this app genuinely collects and stores (matching this project's own "never fabricate, always disclose honestly" discipline, applied here to a real, external-facing form for the first time); a real Closed Testing release built and uploaded. **Verify Play Console's own current, exact Closed Testing tester-count/duration requirements directly inside Play Console at the start of this session** — Google's own published rules for moving from Closed Testing to production changed in 2023 and could change again; don't build this session's plan around a number that might already be stale by the time it runs.

**What must be true before moving on:** nothing — this is the last engineering session in this plan.

**Verification:** a real install of the app via the real, live Play Store Closed Testing link (not a sideloaded APK) on the real device, confirmed to sign in and work identically to every other real, direct-install verification this project has already done.

**Expected result:** Quorum is a real, installable, Play-Store-hosted Android application — the last item in the original "fully working, production-ready project" goal, achieved for real, for free, without compromising any already-built real functionality.

---

## Standing, parallel, owner-only actions (start anytime, block nothing except what's named)

- **Credential rotation** (`specs/tier3_verification/CREDENTIAL_ROTATION_CHECKLIST.md`, already real and ready) — no engineering dependency on this plan at all; good hygiene to complete before Session 12 increases this app's real, public-adjacent exposure, but doesn't have to happen in any particular order otherwise.
- **`mem0.ai` signup** — gates Session 10 specifically, nothing else. Start whenever convenient; the earlier it's done, the more scheduling freedom Session 10 has.

## Genuinely open question, not silently decided either way

**Should the server-side `CalendarAdapter` (the real privacy boundary `DEC-152` deliberately left unbuilt) be reopened too?** Decision 1 reopens *scope* deferrals; this was framed as a privacy decision, not a scope one, and this plan does not assume Preethish's "reopen everything" answer was meant to include overriding a boundary about what data leaves the device. If the answer is yes, it's real, scoped, buildable work (Phase 5's own text already names the right minimal version — a thin record of only externally-booked events, never a full calendar mirror) — but it needs its own explicit yes first.

---

*This plan closes when Session 12's own real, live Play Store install is confirmed. At that point, every phase of `QUORUM_PRODUCTION_COMPLETION_PLAN.md`, every deliberately-deferred scope decision, and this document's own twelve sessions are all real, tested, and verified — the actual, complete, production-grade end state this whole project has been building toward.*
