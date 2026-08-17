# Handbook 04 — Negotiation, Explained

**Milestone reached:** `IMPL_21` — negotiation, the project's headline feature, is complete.

## What negotiation actually is, without the jargon

Most of what Quorum does is one thing happening at a time — an email drafted, an expense logged. Negotiation is different. It's what happens when two or three real parts of your life genuinely collide — a meeting request that would blow past a deadline *and* cost more than you've budgeted. Instead of picking one side or guessing, Quorum brings each affected part of your life into the conversation, on equal footing, and works out real options.

## Why "computing" a conflict is different from "guessing" one

The first, most important design choice: whether a real conflict exists is never left up to an AI model's judgment. It's arithmetic. Does this request need more time than you actually have free? Does it cost more than you have left in the relevant budget? Those are answerable by comparison, not opinion — so that's exactly how Quorum answers them. Only once a *genuine* conflict is confirmed — not a guess, a real comparison against real numbers — does anything more expensive or judgment-based get involved.

One more detail worth knowing: a conflict only counts as a "negotiation" if it touches **two or more** real areas of your life at once. If just one thing is over budget, that's an ordinary correction, handled the normal way. Negotiation is reserved for the genuinely three-dimensional problems — because those are the ones a single, simple check can't resolve well on its own.

## How the actual disagreement gets resolved, and the part I'm proudest of

Here's the part worth remembering: when Calendar, Finance, or Tasks each has something real to say about a conflict, none of them gets to invent a random solution out of nowhere. Each one proposes its own honest fix — "move it," "ask for a waiver," "push the deadline" — and then those *real* proposals get combined into two complete options for you to choose from, plus the option to do nothing.

The reason "combined, not invented" matters: it would be easy for an AI model, asked to synthesize a solution, to make something up that sounds reasonable but isn't actually grounded in anything real. Quorum's synthesis step is built so that never happens quietly — every synthesized option is checked afterward against which real proposals actually existed, and if an option ever referenced something no one actually proposed, that's caught and flagged as an error, not silently accepted.

## The numbers you'd actually see are real, computed numbers — never generated text pretending to be numbers

When Quorum shows you "this option costs you 2 hours of slack but saves ₹500," that number isn't written by an AI describing what it thinks would happen. It's computed — the same option, run against your real, current numbers, with the actual result measured and reported. Run the exact same option through the exact same starting point a hundred times, and you'd get the exact same number every time. That's deliberate, and it's tested specifically that way.

## How to talk about this in an interview

*"I built a multi-agent negotiation system where competing priorities each get an independent voice — but I was careful to keep two things deterministic rather than AI-driven: whether a conflict is real at all, and what the actual numeric impact of each option is. The only part that genuinely uses a model is combining each side's own proposal into a coherent set of choices, and even that step is mechanically checked afterward to make sure nothing gets invented that wasn't actually proposed by a real agent."*
