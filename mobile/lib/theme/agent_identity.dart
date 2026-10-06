// Real, shared agent identity (`DEC-189`, product rebuild Block A).
//
// WHY THIS FILE EXISTS, and why it is the first thing the rebuild
// builds: a direct, confirmed user report drove this whole redesign --
// "the app is not currently an agentic AI app, none of the AI features
// reflect in the app." A real cause of that, found while diagnosing it,
// is that this project's five agents were genuinely real in the backend
// (`agents/email_agent.py` and its four siblings, each a separately
// authorized, domain-scoped LangGraph node) and had NO representation
// in the app whatsoever. Nothing on any screen named an agent, showed
// which one acted, or distinguished one from another. A user could not
// perceive an agent because the UI never mentioned one.
//
// So agent identity is modeled here, once, as real shared data rather
// than being re-invented per screen: a color, an icon, a name, and a
// one-line purpose, keyed by the same real domain strings the backend
// already uses in `action_events` and in `QuickCaptureResult.domain`.
// Every screen that shows an agent reads from this file, so the Email
// agent is the same blue with the same icon on Today, on the Agents
// index, in the live pipeline, and in the Activity timeline.
//
// REAL CONSTRAINT THIS FILE MUST HONOR, carried forward unchanged from
// `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §12.1 even though `DEC-189`
// deliberately supersedes that section's light-primary, no-chromatic-
// identity VISUAL direction: color must never be the only carrier of
// meaning. Hence every agent has a genuinely distinct `icon` as well as
// a distinct `accent`, and callers are expected to render both. The
// aesthetic changed; the accessibility rule did not.
//
// NOTE ON PURPLE, deliberately: §12.1 avoids purple as the industry-
// default "this is AI" brand color. That reasoning is about a product's
// single dominant brand identity, and it is honored -- Quorum's own
// identity color is the Gate's cyan, and purple appears only as one
// functional per-domain accent among six, exactly the "color reserved
// purely for functional signaling" use §12.1 itself endorses.

import 'package:flutter/material.dart';

/// The real, closed set of actors this product has. Five domain agents,
/// plus the Gate, which is deliberately NOT a sixth agent: it is the
/// verification authority that reviews all five, and giving it a
/// distinct identity here keeps "an agent proposed this" and "the Gate
/// checked it" visually separable everywhere in the app.
enum QuorumAgent { email, calendar, tasks, finance, career, gate }

/// Real, shared presentation data for one agent.
@immutable
class AgentIdentity {
  /// The real backend domain string (`QuickCaptureResult.domain`,
  /// `action_events` rows). `gate` deliberately has no backend domain
  /// of its own and uses the literal `"gate"`, which no real action row
  /// ever carries -- see [agentForDomain].
  final String domain;

  final String name;

  /// One honest line about what this agent actually does in this
  /// system -- not marketing copy. Rendered on the Agents index and in
  /// onboarding, so it must stay true to what the backend really does.
  final String purpose;

  final Color accent;
  final IconData icon;

  const AgentIdentity({
    required this.domain,
    required this.name,
    required this.purpose,
    required this.accent,
    required this.icon,
  });
}

/// The real identity table. Six entries, exhaustive over [QuorumAgent].
///
/// Accent choices are deliberately spaced around the hue wheel so that
/// two agents are never confusable at a glance on a dark ground, and
/// every one of them clears a readable contrast against the near-black
/// base in `quorum_dark_theme.dart`. The Gate's cyan sits apart from
/// all five domain hues on purpose: it is the authority over them, not
/// a peer in the same set.
const Map<QuorumAgent, AgentIdentity> kAgentIdentities = {
  QuorumAgent.email: AgentIdentity(
    domain: 'email',
    name: 'Email',
    purpose: 'Reads your inbox, drafts replies, and sends only what you approve.',
    accent: Color(0xFF4A9EFF),
    icon: Icons.mail_outline_rounded,
  ),
  QuorumAgent.calendar: AgentIdentity(
    domain: 'calendar',
    name: 'Calendar',
    purpose: 'Watches your schedule for conflicts and books time when you ask.',
    accent: Color(0xFFA77BFF),
    icon: Icons.event_outlined,
  ),
  QuorumAgent.tasks: AgentIdentity(
    domain: 'tasks',
    name: 'Tasks',
    purpose: 'Captures commitments and keeps deadlines from colliding.',
    accent: Color(0xFF3DD68C),
    icon: Icons.check_circle_outline_rounded,
  ),
  QuorumAgent.finance: AgentIdentity(
    domain: 'finance',
    name: 'Finance',
    purpose: 'Logs spending, tracks the budget, and spots recurring charges.',
    accent: Color(0xFFFFB443),
    icon: Icons.account_balance_wallet_outlined,
  ),
  QuorumAgent.career: AgentIdentity(
    domain: 'career',
    name: 'Career',
    purpose: 'Tracks applications and interviews, and surfaces what is going stale.',
    accent: Color(0xFFFF5FA2),
    icon: Icons.work_outline_rounded,
  ),
  QuorumAgent.gate: AgentIdentity(
    domain: 'gate',
    name: 'The Gate',
    purpose: 'Independently verifies every agent before anything real happens.',
    accent: Color(0xFF22D3EE),
    icon: Icons.verified_user_outlined,
  ),
};

/// Convenience accessor. Total by construction -- [kAgentIdentities] is
/// exhaustive over the enum, so this can never return null and callers
/// never need a null check.
AgentIdentity identityOf(QuorumAgent agent) => kAgentIdentities[agent]!;

/// Maps a real backend domain string onto an agent.
///
/// Returns `null` rather than guessing or defaulting, deliberately. The
/// domain strings come from real server responses, and silently
/// rendering an unrecognized domain as (say) the Email agent would show
/// a user a confident, wrong attribution -- precisely the kind of
/// quiet mislabeling this project's honesty rules exist to prevent. A
/// null here is the caller's signal to render a real neutral/unknown
/// treatment instead, which is honest.
///
/// Case-insensitive and whitespace-tolerant, because these strings
/// arrive over HTTP from several different real producers.
QuorumAgent? agentForDomain(String? domain) {
  if (domain == null) return null;
  final normalized = domain.trim().toLowerCase();
  if (normalized.isEmpty) return null;
  for (final entry in kAgentIdentities.entries) {
    if (entry.value.domain == normalized) return entry.key;
  }
  return null;
}

/// The five real domain agents, in the fixed order every surface in the
/// app displays them. Deliberately excludes [QuorumAgent.gate], which is
/// not a domain agent and gets its own dedicated tab.
///
/// The order is itself a product decision rather than alphabetical:
/// Email and Calendar first because they are the two domains with real
/// external side effects and therefore the two a user most needs to
/// keep an eye on, then the three internal-state domains.
const List<QuorumAgent> kDomainAgents = [
  QuorumAgent.email,
  QuorumAgent.calendar,
  QuorumAgent.tasks,
  QuorumAgent.finance,
  QuorumAgent.career,
];
