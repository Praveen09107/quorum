# Handbook 05 — The Complete App, Walked Through

**Milestone reached:** `MOBILE_22` — a person can open the app and actually reach real, working screens. This is the last of five handbook entries, and the only one written after the whole system — backend and mobile both — was real at once.

## What this app actually is, in one paragraph, without the architecture diagram

Quorum is a phone app that handles your email, calendar, tasks, finances, and job search — but the thing that makes it different isn't what it does, it's how it earns the right to act on your behalf. Every single time it's about to do something in the real world — send an email, move a meeting, log an expense — that action passes through an independent checking layer before you ever see it, and the more consequential the action, the more scrutiny it gets. Nothing about that checking layer is optional, and nothing about it is something the AI doing the work can turn off for itself.

## The one idea everything else in this app is built around

Most AI assistants ask you to trust them. Quorum is built around a different idea: **don't ask to be trusted — be checked, and show the checking.** Concretely, that means three real, separate things happen for anything that matters: a fast, deterministic layer verifies simple facts (does this meeting actually exist? does this number actually add up?) before any AI model is even involved; a second, genuinely different AI model — not the one that drafted the action — reviews anything with real stakes, specifically because a second, differently-trained reviewer catches different mistakes than the original author would catch in itself; and every single result, whether the system got it right or caught its own mistake, is written to a log you can actually read, with the failures given the exact same visual weight as the successes — never buried, never smaller text, never a second tab you'd have to think to check.

## How the pieces actually connect — the honest, physical shape of the system

The backend is the part that does real work: reads your email, checks your calendar, computes your actual budget, and runs every proposed action through the verification layer described above. It's a real, tested Python service — 156 tests, every one of them run and shown, not claimed from memory — organized around five independent domain agents (Email, Calendar, Tasks, Finance, Career) that each propose actions, and a shared Gate that every proposal passes through regardless of which agent made it.

The phone app is where you actually see and approve things. It has four places you'd normally go: **Today**, which shows what genuinely needs your attention right now, what's holding steady on its own, and what's actively being negotiated; **Log**, an honest record of everything the system has done, successes and mistakes side by side; **Trust**, which shows how the system performs when tested against scenarios specifically designed to try to fool it; and **You**, where your account actually lives, including the ability to permanently delete everything.

**The honest, current state of the connection between them:** the phone app is built to talk to the real backend once it's deployed somewhere with a real address — every screen already knows exactly what data it needs and how to ask for it, but that live connection itself hasn't been made yet. This isn't a gap being hidden; it's the natural next real step, named directly in this project's own status records.

## The two moments in this app that are genuinely unlike anything else here

**Watching the Gate work.** Most apps that use AI just show you the result. Quorum has a screen — reachable the moment any action needs your approval — that shows you the actual verification trace: what the fast, deterministic checks found, and if the action was consequential enough, what the independent AI reviewer specifically raised or explicitly signed off on. You're not asked to trust the output. You're shown the work.

**Watching a real disagreement get resolved.** When two parts of your life genuinely conflict — a meeting that would blow past a deadline and cost more than you've budgeted — Quorum doesn't quietly pick a side or invent a compromise out of nowhere. Calendar, Finance, and Tasks each state their own real concern, and you're shown two complete, honestly computed options plus the choice to do nothing, with the actual numeric consequences of each — never a made-up number, always a real one, computed the same way every time you'd ask.

## What's genuinely true right now, and what genuinely isn't yet — stated plainly, the way this whole project insists on

**True:** the entire backend — all five domains, the full verification Gate, negotiation, authentication, thirteen supporting feature modules — is real, tested, and running. Every mobile screen a person would actually use is real and correct, connected into a working four-tab app for the first time as of the session right before this one. A real layout bug was found and fixed before it ever shipped. A real cross-language arithmetic disagreement between Python and Dart was found, and rather than guess at the answer, left honestly unresolved until a real compiler can settle it.

**Not yet true:** the phone app isn't talking to a live backend yet — that's real infrastructure work, not a code problem. Seven real, already-built screens (career tracking, finance details, search, and others) aren't reachable from the app's everyday navigation yet — they exist and work, they just don't have a considered place in the menu structure. And the self-test harness that measures how well the verification Gate catches mistakes is still testing against a simplified stand-in for the real Gate, not the real thing — a fact that was found stale in its own documentation and corrected on the spot, rather than left to mislead anyone who read it next.

## How to talk about this in an interview

*"I built a personal-assistant app where the AI doing the work is never the only thing checking the work. Every proposed action passes through an independent verification layer — fast deterministic checks first, then a genuinely different AI model as reviewer for anything consequential — and the system logs its own failures with the same visibility as its successes, by design, not as an afterthought. What I'm most proud of isn't any single feature — it's the discipline behind building it: I never claimed a test passed without actually running it, I flagged real uncertainties instead of guessing past them, and when I found gaps — a stale doc making a false claim, a genuine cross-language arithmetic disagreement, a whole app's worth of real screens that weren't actually wired together yet — I fixed what was honestly fixable in scope and named what wasn't, rather than paper over either one."*
