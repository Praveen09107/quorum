# Handbook 01 — The Gate, Explained

**Milestone reached:** `IMPL_08` — the Gate is real, tested, and complete.

## What the Gate actually is, without the jargon

Imagine every time Quorum wants to do something — send an email, log an expense, book a meeting — it has to pass through a checkpoint first. That checkpoint is the Gate. Nothing gets through without being checked, and how hard it gets checked depends on how much it would matter if it were wrong.

## The two kinds of checking, and why both exist

**The first kind is just looking things up.** Does this meeting actually exist on the calendar? Is this expense actually within budget? These are questions a computer can answer for certain, instantly, for free — so Quorum never wastes an AI model's time on them. This is "Stage A."

**The second kind needs real judgment.** Does this email sound like something you'd actually send? Does this draft imply a promise you never actually made? These aren't yes/no lookups — they need something closer to human judgment. This is "Stage B," and it's the only place an AI model actually gets involved in deciding whether something is okay.

The reason this split matters: it means Quorum never asks an expensive, slower AI model to answer a question a database could answer for free and instantly. That's not just efficient — it's *more reliable*, because a lookup is never wrong the way a model's guess occasionally can be.

## The part that makes Stage B trustworthy, not just present

Here's the detail worth actually understanding, because it's the most distinctive thing about how Quorum verifies itself: the AI model that *drafts* something and the AI model that *checks* it are deliberately different models, from different companies. One drafts (Google's Gemini), one criticizes (a different model, via Groq), and a third — sometimes the same as the drafter, sometimes not — makes the final call.

Why does that matter? If the same model checked its own work, it might miss the exact same blind spots it had while writing it in the first place — the same way it's hard to proofread your own writing. A genuinely different model, trained differently, is much more likely to actually catch something the first one missed.

## The three-way answer, not just yes or no

When Stage A checks a fact — like "does this meeting exist" — it doesn't just say yes or no. It can also say "I genuinely don't know." That third option matters more than it sounds like it should: if Quorum only had yes/no, an honest "I couldn't find this" would either get treated as a lie (unfair, since it might just be a meeting that was never entered into the calendar) or silently ignored (dangerous, since real uncertainty would disappear). Keeping "I don't know" as its own real answer means Quorum never has to pretend to be more certain than it actually is.

## The one thing that never, ever changes

No matter how confident every single check comes back, if an action would actually leave the system — an email genuinely sent, a calendar invite genuinely sent to a real person — a real human has to tap approve first. Every time. Even if the system is somehow running with no internet connection, that rule doesn't bend; the action just waits until it can be properly checked.

## How to talk about this in an interview

*"I built a two-stage verification system for an AI agent — deterministic checks for anything that's actually a fact, and adversarial AI review, using two different AI providers, for anything that's a genuine judgment call. The key design decision was making sure the model that drafts something is never the only one checking it — that's a real, deliberate defense against a model missing its own mistakes."*

That's a complete, honest, technically real answer — because it's exactly what got built, tested, and verified, not a simplified version of something bigger that never actually worked.
