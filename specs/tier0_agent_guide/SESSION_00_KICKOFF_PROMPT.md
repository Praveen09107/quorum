# Quorum — Session 00 Kickoff Prompt

**Tier:** `tier0_agent_guide` · **Purpose:** the literal message sent to Claude Code to begin real implementation work on Quorum, for the first time. Saved here as a permanent record of how the engagement actually started — not meant to be re-sent verbatim for every future session; `/quorum-session-start` handles that ongoing ritual.

---

## The prompt

```
I'm starting real implementation work on Quorum for the first time. Before you write anything, I need you to get properly oriented — this is a real, substantial project with a full specification set behind it, and I'd rather you spend the time understanding it correctly now than build something that has to be undone later.

Read these four files completely, in this order, before responding:

1. .claude/CLAUDE.md (should already be loaded automatically — confirm with /memory if you're unsure)
2. specs/tier1_foundation/QUORUM_PROJECT_OVERVIEW.md
3. specs/tier3_verification/STATUS_INDEX.md
4. specs/tier1_foundation/QUORUM_IMPLEMENTATION_STRATEGY.md

Here's the real context those documents will fill in more deeply, stated plainly up front: I'm a solo developer building this as a portfolio project toward a career goal of becoming an AI Engineer. I'm a beginner at hands-on coding — I direct and approve, you generate the actual implementation. There's no other developer reviewing this code, and no human backstop catching a subtle bug before it ships. That's not a disclaimer, it's the reason the verification discipline in this project's own methodology (and in Quorum's own architecture) matters as much as it does — please hold yourself to that same standard throughout, not just when I ask.

What I need from you, in terms of how you communicate: explain *why*, not just *what*, whenever a decision isn't obvious. I don't need the spec-driven methodology itself re-explained — I've used this exact approach before on a prior project — but do over-explain anything genuinely Quorum-specific, especially your own reasoning when you make a judgment call the spec leaves open.

Here's how the rest of this engagement is going to unfold, so you understand the shape of the whole thing even though I'm only asking you to start the first piece: QUORUM_IMPLEMENTATION_STRATEGY.md lays out seven real phases (Phase 0 through Phase 6) from here through production, each with a concrete, checkable gate before the next one starts. We are not going to attempt all seven in one uninterrupted run — we're going to work through them one at a time, with real verification at every gate, the same discipline every session in this project's history has already been held to. If you ever find yourself wanting to skip ahead to a later phase because it seems more interesting or more useful, stop and flag that rather than doing it — Phase order exists for real, documented reasons (see the Gate reasoning in each phase's own section).

Right now, I need you to begin Phase 0 specifically — the structural repository migration described in QUORUM_IMPLEMENTATION_STRATEGY.md's Phase 0 section, applying the layout specified in QUORUM_PROJECT_STRUCTURE.md to the real, already-complete codebase. Nothing else yet.

Before you touch a single file, run /quorum-session-start and show me its output. Then, before writing any code, give me a short summary in your own words of: what Phase 0 actually involves, what the real gate is that proves it's done correctly, and anything in the current codebase state that seems ambiguous or worth confirming with me before you proceed. I want to catch any misunderstanding now, while it costs nothing to fix, rather than after you've already moved files around.
```

---

## Why this prompt is shaped the way it is

**It asks for a read-back before any code, deliberately.** The single highest-value, lowest-cost thing to do at the start of a large, multi-phase engagement is catch a misunderstanding while it's still just a misunderstanding — before it's also a diff. This isn't distrust; it's the same "verify before proceeding" discipline that produced every real test and every real fix across this project's own history.

**It explains the whole six-phase shape while scoping the actual ask to Phase 0 alone.** Without that context, Claude Code has no way to know that skipping ahead to, say, Phase 3's integration wiring would be a real, documented mistake rather than a reasonable initiative — the phase-gate structure only prevents drift if the agent doing the work actually understands why it exists.

**It restates the personal/beginner context directly, even though `CLAUDE.md` already has it.** `CLAUDE.md`'s version is the permanent, operational instruction. This restates it once, in the user's own words, at the one moment — the very first real session — where it matters most that it's genuinely internalized, not just present in a file that gets auto-loaded and potentially skimmed.

---

*Related: `.claude/commands/quorum-session-start.md`, `specs/tier1_foundation/QUORUM_PROJECT_OVERVIEW.md`, `specs/tier1_foundation/QUORUM_IMPLEMENTATION_STRATEGY.md`.*
