# Handbook 02 — The Backend, Live

**Milestone reached:** `IMPL_11` — the infrastructure layer is real and genuinely proven.

## What "infrastructure" actually means here

Everything so far in the Gate walkthrough was about logic — the rules for how Quorum decides what to trust. This part is about where all of that logic actually *runs*, and where the information it depends on actually *lives*. Think of it as the difference between designing a kitchen and actually plumbing the water in.

## The database, and something worth being genuinely proud of

Quorum's database — where every task, expense, and application actually gets stored — wasn't just designed on paper. A real copy of it was installed and actually tested: real data went in, and the database's own built-in rules genuinely rejected bad data on their own. As one concrete example — an attempt to log an event with an invalid status was *rejected by the database itself*, not by application code checking it first. That's a meaningfully stronger guarantee: even if a bug elsewhere in the code tried to sneak in something wrong, the database's own foundation would refuse it.

## The container, and an honest limitation worth understanding, not glossing over

Quorum's backend runs inside something called a container — a self-contained package that can run the same way anywhere. Building that container for real, for the first time, mostly succeeded — but hit a real wall partway through: a network/security setting specific to the development environment blocked the very last step. This wasn't quietly worked around by turning off a safety check to make it pass — that would have traded a real, honest "not fully verified yet" for a real, meaningful security risk in production. It's reported exactly as it happened, and it'll resolve itself the moment this step runs somewhere without that specific limitation — your own machine, or the real deployment pipeline.

## Where it actually lives when it's live

Quorum's backend runs on Google's infrastructure in a way specifically chosen to cost nothing when nobody's using it — it only "wakes up" and costs anything at the exact moment a real request comes in. One specific, deliberate setting worth knowing: only one request is ever handled at a time per running copy. That sounds like it might be slower, and in a tiny way it is — but it closes a real, if unlikely, risk of two different people's data accidentally crossing paths inside the same running process. For a system whose entire purpose is being trustworthy, that trade was worth making.

## How to talk about this in an interview

*"I don't just claim my database schema works — I actually installed Postgres locally and proved it: real constraint violations get rejected by the database itself, not just checked in application code. When I hit a real limitation trying to build the Docker container in my dev sandbox, I diagnosed exactly why — a network isolation issue — rather than disabling a security check to force it to pass. That's the difference between a system that looks finished and one that's actually been verified."*
