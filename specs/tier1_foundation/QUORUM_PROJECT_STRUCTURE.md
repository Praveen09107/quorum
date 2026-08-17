# QUORUM — Project Directory Structure

**Tier:** `tier1_foundation` (structural reference — stable once adopted, amended not rewritten) · **Volatility:** Low. This document describes the *shape* of the repository, not its live contents — it should change only when a genuinely new top-level concern is added (a new deployable service, a new infra target), not every time a session adds a file inside an already-defined folder.

**Purpose:** this is the single, canonical reference for what the Quorum repository *should* look like — every folder that should exist, every file that should exist right now, and an explicit, unambiguous line between the two. It exists for two real readers: a human developer opening this repository for the first time, and Copilot (or any coding agent) verifying, before writing anything, whether a given folder or file is something it should create fresh or something that already has a defined home here.

**A style note, stated honestly rather than silently:** a stylistically-similar reference document exists from a different project and a different conversation; it isn't accessible in this working environment, so this document follows the documentation conventions already established and proven within Quorum itself — the same `Tier`/`Volatility` header, real citations to actual files, and reasoned "why" for every structural decision used throughout `specs/tier1_foundation/` and `specs/tier3_verification/`.

---

## 1. How to use this document — the one rule that matters most

**Every folder shown below should exist now. Not every file shown below should exist now.** Two categories, and this document marks every file explicitly as one or the other:

- **`[CREATE NOW]`** — structural, onboarding, or configuration files with no session-specific business logic. These are created once, as part of setting up the repository, and rarely change afterward.
- **`[COPILOT — see IMPL_XX / MOBILE_XX]`** — real application code whose actual content is the subject of a specific, already-written session document under `specs/tier2_implementation/` or `specs/tier4_mobile/`. Do not write this content from this structure document alone — the session document is the actual spec; this document only confirms *where* the result belongs.

Before creating any file, check which category it falls into. If it's `[COPILOT]`, go read its named session document first — this structure document tells you the destination, not the content.

---

## 2. The complete reference directory tree

```
quorum/
├── README.md                                  [CREATE NOW]
├── LICENSE                                     [CREATE NOW — see §5, requires your decision]
├── CONTRIBUTING.md                             [CREATE NOW]
├── CODE_OF_CONDUCT.md                          [CREATE NOW]
├── SECURITY.md                                 [CREATE NOW]
├── QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md       (real, already exists)
├── QUORUM_SPEC_METHODOLOGY.md                   (real, already exists)
├── .gitignore                                   (real, already exists)
├── .editorconfig                               [CREATE NOW]
├── .env.example                                [CREATE NOW]
├── docker-compose.yml                           (real, already exists — local dev orchestration)
│
├── .claude/
│   └── CLAUDE.md                                (real, already exists)
│
├── .github/
│   ├── workflows/
│   │   └── ci.yml                               (real, already exists)
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md                       [CREATE NOW]
│   │   └── feature_request.md                  [CREATE NOW]
│   └── PULL_REQUEST_TEMPLATE.md                [CREATE NOW]
│
├── handbook/                                    (real, already exists — 6 files, HANDBOOK_00–05)
│
├── specs/                                       (real, already exists — do not restructure)
│   ├── tier0_agent_guide/
│   ├── tier1_foundation/
│   │   └── QUORUM_PROJECT_STRUCTURE.md          (this document, once saved)
│   ├── tier2_implementation/
│   ├── tier3_verification/
│   └── tier4_mobile/
│
├── backend/
│   ├── README.md                               [CREATE NOW — backend-specific quickstart]
│   ├── pyproject.toml                          [CREATE NOW]
│   ├── requirements.txt                         (real, already exists)
│   ├── Dockerfile                                (real, already exists)
│   ├── .env.example                            [CREATE NOW — backend-specific var names]
│   │
│   ├── src/
│   │   └── quorum_backend/
│   │       ├── __init__.py                     [CREATE NOW — empty package marker]
│   │       ├── main.py                         [COPILOT — already real; relocate + fix imports per migration]
│   │       ├── router.py                       [COPILOT — already real; relocate + fix imports per migration]
│   │       │
│   │       ├── core/
│   │       │   ├── __init__.py                 [CREATE NOW]
│   │       │   ├── config.py                   [COPILOT — new module; see §6, no session doc yet, treat as a real gap to close]
│   │       │   └── logging.py                  [COPILOT — new module; same as above]
│   │       │
│   │       ├── gate/
│   │       │   ├── __init__.py                 [CREATE NOW]
│   │       │   └── (schemas.py, prompts.py, validators.py, orchestration.py — all real, already exist; see IMPL_01–IMPL_08)
│   │       │
│   │       ├── agents/
│   │       │   ├── __init__.py                 [CREATE NOW]
│   │       │   └── (5 domain agents + tool_authorization.py — real, already exist; see IMPL_13–IMPL_17)
│   │       │
│   │       ├── negotiation/
│   │       │   ├── __init__.py                 [CREATE NOW]
│   │       │   └── (trigger, positions, synthesis, impact_simulator, subgraph — real, already exist; see IMPL_18–IMPL_21)
│   │       │
│   │       ├── auth/
│   │       │   ├── __init__.py                 [CREATE NOW]
│   │       │   └── (access_token, refresh_token, oauth_pkce — real, already exist; see IMPL_12)
│   │       │
│   │       ├── security/
│   │       │   ├── __init__.py                 [CREATE NOW]
│   │       │   └── (trace_scrubbing, account_deletion, memory_transparency — real, already exist; see IMPL_22, MOBILE_19)
│   │       │
│   │       └── features/
│   │           ├── __init__.py                 [CREATE NOW]
│   │           └── (11 real feature modules — see their respective IMPL/MOBILE session docs)
│   │
│   ├── migrations/
│   │   └── 0001_initial_schema/
│   │       ├── up.sql                          [COPILOT — content already real in the current 001_initial_schema.sql; relocate + split into up/down per the migration guidance in the prior structural turn]
│   │       └── down.sql                        [COPILOT — genuinely new; no rollback path existed before this restructure]
│   │
│   └── tests/
│       ├── __init__.py                         [CREATE NOW]
│       └── (mirrors src/quorum_backend/ exactly — gate/, agents/, negotiation/, auth/, security/, features/, each real, already exist; see their respective session docs)
│
├── mobile/
│   ├── README.md                               [CREATE NOW — mobile-specific quickstart]
│   ├── pubspec.yaml                              (real, already exists)
│   ├── analysis_options.yaml                   [CREATE NOW — currently genuinely missing, a real gap]
│   ├── .env.example                            [CREATE NOW — mobile-specific var names, if any real ones exist]
│   │
│   ├── lib/
│   │   ├── main.dart                           [COPILOT — already real; see MOBILE_01]
│   │   ├── shell/                               (real, already exists — see MOBILE_01, MOBILE_22)
│   │   ├── theme/                               (real, already exists — see MOBILE_01)
│   │   ├── db/                                  (real, already exists — see MOBILE_01)
│   │   ├── model/                               (real, already exists — see MOBILE_02)
│   │   ├── config/                              (real, already exists — see MOBILE_02)
│   │   ├── privacy/                             (real, already exists — see MOBILE_03)
│   │   └── features/
│   │       ├── today/                           (real — see MOBILE_04–MOBILE_07)
│   │       ├── gate_reveal/                     (real — see MOBILE_08)
│   │       ├── negotiation/                     (real — see MOBILE_09)
│   │       ├── waiting_on/                      (real — see MOBILE_10)
│   │       ├── career/                          (real — see MOBILE_11)
│   │       ├── career_digest/                   (real — see MOBILE_12)
│   │       ├── finance/                         (real — see MOBILE_13)
│   │       ├── search/                          (real — see MOBILE_14)
│   │       ├── honesty_log/                     (real — see MOBILE_15)
│   │       ├── trust/                           (real — see MOBILE_16)
│   │       ├── trust_digest/                    (real — see MOBILE_17)
│   │       ├── you/                             (real — see MOBILE_18)
│   │       ├── memory_transparency/             (real — see MOBILE_19)
│   │       ├── outage/                          (real — see MOBILE_20)
│   │       └── tasks/                           (real — see MOBILE_23)
│   │
│   └── test/                                    (real, already exists — mirrors lib/features/ structure)
│
├── infra/
│   ├── README.md                               [CREATE NOW — explains what belongs here and what doesn't yet]
│   ├── docker/
│   │   └── docker-compose.local.yml            [COPILOT — relocated from root docker-compose.yml, no content change]
│   ├── cloud_run/
│   │   └── service.yaml.template               [COPILOT — genuinely new, no real Cloud Run project exists yet; see STATUS_INDEX.md open item 3]
│   ├── supabase/
│   │   └── README.md                           [CREATE NOW — provisioning steps only, never real credentials]
│   └── github_actions/
│       └── deploy-cutover.yml.template          [COPILOT — the deferred CI stage named in DEC-003; a real home for it now, still deferred until a real Cloud Run target exists]
│
└── scripts/
    ├── README.md                               [CREATE NOW — what each script does and when to run it]
    ├── setup_dev_env.ps1                       [CREATE NOW — real, working local setup automation]
    ├── run_migrations.ps1                      [COPILOT — depends on the real migration tool decision, not yet made]
    └── seed_demo_data.ps1                      [COPILOT — depends on real demo data shape, not yet specified]
```

---

## 3. Folder-by-folder reasoning — why each one belongs, and what it must never contain

| Folder | Why it exists | What must never end up here |
|---|---|---|
| `specs/` | The actual source of truth for every real decision. Nothing in this document overrides it — this document is a map, `specs/` is the territory. | Live runtime status (that's `STATUS_INDEX.md`'s job specifically, not the tier as a whole) |
| `backend/src/quorum_backend/` | The src-layout convention, adopted specifically because the current flat top-level module names (`gate`, `agents`, `router`) risk colliding with third-party package names on `PYTHONPATH` — a real production risk invisible in a demo | Test files (those belong in `backend/tests/`, mirroring this tree exactly, never interleaved) |
| `backend/src/quorum_backend/core/` | The one backend addition with no existing session document — closes a real, verified gap: no runtime settings/config module exists anywhere in the current codebase, confirmed by direct search before writing this document | Business logic — this folder is infrastructure-for-the-app, not the app itself |
| `infra/` | Everything currently missing that a real deployment needs (Cloud Run service definition, the deferred CI stage from `DEC-003`) gets a home that doesn't require touching application code the day it's actually provisioned | Real credentials, real project IDs — templates and placeholders only, ever |
| `scripts/` | Local dev ergonomics in one discoverable place, not scattered ad-hoc commands only the original developer remembers | Anything that's actually part of the deployed application |
| `.github/` | Fixed by GitHub's own requirement — cannot be moved regardless of preference | — |

---

## 4. What goes in each `[CREATE NOW]` file — real, actionable content, not placeholders

**`README.md` (root)** — the front door. Should cover, in order: one paragraph on what Quorum is (the trust-architecture pitch, matching `HANDBOOK_05`'s framing), the real current status (a link to `STATUS_INDEX.md`, never a restated number — the exact lesson the full specification audit already proved the hard way), local setup (link to `scripts/setup_dev_env.ps1`), and a link to `QUORUM_SPEC_METHODOLOGY.md` for anyone about to start a new session.

**`LICENSE`** — **requires your decision, not mine.** This is a real business choice (open portfolio piece vs. proprietary work), not a technical one, and choosing it for you would be exactly the kind of unrequested decision this project's own discipline exists to avoid. Leave a placeholder noting "LICENSE TBD — see repository owner" until decided.

**`CONTRIBUTING.md`** — should describe the *real, already-practiced* workflow: the `session/**` branch convention already live in `ci.yml`, the requirement that every session's own document (`IMPL_XX`/`MOBILE_XX`) is attached before work starts, and the review-tier system (STANDARD vs. CRITICAL) exactly as defined in `CLAUDE.md`. This is not a generic open-source contributing guide — it should describe the actual, proven Quorum session methodology.

**`CODE_OF_CONDUCT.md`** — Contributor Covenant is the standard, well-understood default; adopt it as-is unless there's a specific reason not to.

**`SECURITY.md`** — genuinely important here, not boilerplate: Quorum handles real PII (email content, financial data) and has a documented trace-scrubbing/account-deletion security layer (`IMPL_22`). State a real vulnerability-reporting contact and reference the existing `security/` module as evidence this is taken seriously, not just asserted.

**`.editorconfig`** — cross-language consistency (Python 4-space, Dart 2-space, consistent line endings) — prevents exactly the kind of formatting drift `ruff`/`dart format` alone don't fully cover across a mixed-language repo.

**`.env.example`** (root and per-app) — variable *names* only, with safe placeholder values (`SUPABASE_URL=your-project-ref-here`), never real secrets. Directly closes the config-module gap named in the previous structural analysis.

**`backend/pyproject.toml`** — unifies `ruff` and `pytest` configuration (both already used via separate files) and makes the backend a properly installable package, a prerequisite for the `src/` layout above actually working cleanly.

**`mobile/analysis_options.yaml`** — currently genuinely missing; the Dart equivalent of `ruff`, needed for any real lint enforcement in CI going forward.

**Every `__init__.py`** — near-empty, but structurally required the moment `backend/` becomes a real package rather than a `PYTHONPATH`-hack — without them, the `src/quorum_backend/` layout this whole restructure is built around simply doesn't work as a Python package.

---

## 5. The explicit boundary — what Copilot builds, and where it looks first

Every `[COPILOT]`-marked entry above has a named source: an `IMPL_XX` or `MOBILE_XX` session document. **The instruction for any coding agent working in this repository is the same one already established project-wide in `CLAUDE.md`: attach the named session document before writing the corresponding file, verify against the real schema/endpoint/constant before assuming it, and update `STATUS_INDEX.md` and `DECISIONS_LOG.md` when done — never trust this structure document alone for content, only for placement.**
