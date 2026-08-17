# Handbook 00 — How Sessions Actually Work

This is the one document to read before running anything through Claude Code. Everything else in the handbook assumes you understand this first.

## What a "session" is

Every piece of Quorum gets built in a bounded, self-contained chunk called a session — one real feature, one real test, one real approval, before the next one starts. You've already seen the names: `IMPL_00`, `IMPL_13`, `MOBILE_01`, and so on. Each one is a real document, sitting in the `specs/` folder, containing complete, runnable code — never a description of code, never a "fill this in later."

## What you actually do

You don't write anything, and you don't read code. Your job, every single time, is:

1. **Hand a session's spec file to Claude Code.** That's it — point it at the file (`specs/tier2_implementation/IMPL_18_...md`, for example) and let it work.
2. **Wait for the report.** Claude Code runs the real code, runs the real tests, and reports back in plain language — what got built, what got verified, and what the actual test output was. Not "should work." Real output.
3. **Read the report, not the code.** The report is written for you specifically — you were never expected to open the Python files yourself.
4. **Approve or don't.** If the report says everything genuinely passed, you say go ahead, and that session's work becomes permanent (a real commit). If something looks wrong or the report itself says something failed, nothing moves forward until that's resolved.

That's the entire loop. It repeats, one session at a time, until the project is done.

## Why it's built this way, specifically for you

You told me directly that you can't review code and are trusting Claude fully — including to verify its own work, not just to write it. That's a real, unusual constraint, and this whole structure exists because of it. A developer who could read Python might get away with skimming a diff. You can't, so the *verification* has to be strong enough to stand in for you — real tests that actually run, real error messages when something's wrong, never a confident-sounding claim that wasn't actually checked. Every session report you'll ever receive follows this same shape for that exact reason.

## What "high quality" has actually looked like, concretely

Not a slogan — here's what's actually happened, repeatedly, across real sessions: a lint check catching a genuine unused import before it became a habit. A test that was *wrong*, not the code — caught and fixed the same way a code bug would be. A design flaw (a stale-value bug in the Gate's revision logic) found by working through the logic carefully *before* it ever became a real bug in running code. A Docker build that hit a real limitation, honestly reported as unverified rather than quietly worked around with a shortcut that would have been unsafe in production. None of these were hidden from you. All of them are sitting in the real decisions log, `DECISIONS_LOG.md`, in full.

## Where to find things, if you ever want to look

You never have to, but if you're curious: `STATUS_INDEX.md` always has the honest, current answer to "what's actually built right now." `DECISIONS_LOG.md` has the full history of every real decision and every real thing found along the way, including mistakes. Neither requires reading code to understand.

## The one rule that never bends, restated here because it matters most

No action that actually sends something, books something, or spends money ever happens without you personally approving it — every time, no exceptions, regardless of how confident the system is. Everything else in Quorum's design exists in service of that one guarantee.
