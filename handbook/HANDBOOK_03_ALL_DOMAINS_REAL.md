# Handbook 03 — All Five Domains, Real

**Milestone reached:** `IMPL_17` — Email, Calendar, Tasks, Finance, and Career are all real.

## What a "domain agent" actually is

Each part of Quorum's life — email, calendar, tasks, money, career — has its own dedicated worker, and each worker only knows how to do things within its own area. The email worker can draft and send emails. It cannot touch your budget. The finance worker can log an expense. It cannot send an email on your behalf. This isn't a limitation that happened by accident — it's a deliberate security boundary, built and *tested* the same way a lock is tested by actually trying the wrong key.

## The boundary, proven, not just claimed

Here's a concrete thing that actually happened: once all five domains existed, every single domain's tools were tested against every other domain — email against calendar's tools, calendar against finance's, finance against career's, all of them, both directions. Every single one of those attempts was correctly rejected. That's not five separate claims of "this domain is secure" — it's one real test proving the entire system of boundaries holds together as a whole, not just in the specific pairs someone happened to think to check.

## Why five workers instead of one

It would have been simpler to build one AI worker that can do everything. It was deliberately not built that way, for three real reasons at once: it means a mistake in one area (say, a bug in the email logic) can't accidentally spill into another (like the budget); it means when two things genuinely conflict — a meeting request that would blow a deadline and cost money — each area can honestly argue its own case with its own real information, instead of one worker trying to hold every consideration in its head at once; and it means the system stays understandable, one piece at a time, instead of becoming one enormous thing nobody can reason about.

## The one that's different from the rest — Career

Four of the five workers each make one kind of decision. The career worker makes two, depending on what's actually happening: it always updates where an application stands, and — only when a real interview shows up — it also puts together a short research brief on the company, automatically. Both paths were tested separately, including a real edge case: what happens if an interview is detected a moment before the research has actually come back? (Answer, tested and confirmed: nothing gets compiled from nothing. It waits.)

## How to talk about this in an interview

*"I designed the system around domain-scoped agents rather than one general-purpose agent, specifically for the security boundary it creates — each agent only has access to its own tools, enforced at two independent layers, and I proved that boundary holds by testing every domain against every other domain exhaustively, not just spot-checking a few pairs. When I added a fifth agent with genuinely different, branching behavior, I made sure both branches — and a real edge case between them — were proven separately before calling it done."*
