import 'package:flutter/material.dart';

import 'package:quorum_mobile/db/database.dart';
import 'package:quorum_mobile/features/calendar/calendar_logic.dart';
import 'package:quorum_mobile/features/meeting_load/meeting_load_logic.dart';
import 'package:quorum_mobile/theme/agent_identity.dart';
import 'package:quorum_mobile/theme/glass.dart';
import 'package:quorum_mobile/theme/quorum_dark_theme.dart';
import 'package:quorum_mobile/theme/quorum_kit.dart';
import 'package:quorum_mobile/theme/spacing.dart';

/// A real, deliberately minimal display of whatever's currently in the
/// real, on-device `CalendarMirror` table (`db/database.dart`) -- this
/// screen itself never touches the `device_calendar` plugin, permission,
/// or sync at all; it's a pure, testable read of already-fetched data,
/// the same separation-of-concerns `calendar_sync.dart` itself already
/// establishes between the real sync logic and the plugin call.
///
/// `DEC-209` (product rebuild Part C, visual pass): redesigned onto the
/// dark glassmorphic system `agents_index_screen.dart` already
/// established, carrying the Calendar agent's own accent throughout --
/// zero logic change (`sortByStartTime`/`computeWeeklyMeetingLoad`/
/// `formatEventTimeRange`/`formatEventDayLabel` are untouched, same
/// props, same three real states this widget always had).
///
/// [permissionGranted] and [events] are deliberately BOTH passed in,
/// rather than [events] alone deciding the honest empty-state message:
/// an empty mirror with permission genuinely denied ("we were never
/// allowed to look") is a real, different situation from an empty
/// mirror with permission granted ("we looked, and there's genuinely
/// nothing in the next 14 days") -- collapsing the two into one message
/// would misdescribe a real, previously-granted-then-revoked permission
/// case, or a first-ever open before any sync has run at all.
class CalendarScreen extends StatelessWidget {
  final List<CalendarMirrorData> events;
  final bool permissionGranted;
  final DateTime now;

  const CalendarScreen({
    super.key,
    required this.events,
    required this.permissionGranted,
    required this.now,
  });

  @override
  Widget build(BuildContext context) {
    final identity = identityOf(QuorumAgent.calendar);

    return QuorumAmbientBackground(
      accent: identity.accent,
      child: SafeArea(
        // `DEC-209`: this screen is PUSHED behind a transparent,
        // `extendBodyBehindAppBar: true` app bar (kept only for its
        // real back button -- see `CalendarLoader`'s own docstring),
        // so real content needs to start below the real toolbar
        // height, not just the system status bar `SafeArea` alone
        // accounts for.
        child: Padding(
          padding: const EdgeInsets.only(top: kToolbarHeight - QuorumSpacing.md),
          child: events.isEmpty
              ? _EmptyBody(permissionGranted: permissionGranted, identity: identity)
              : _EventsBody(events: events, now: now, identity: identity),
        ),
      ),
    );
  }
}

class _AgentHeader extends StatelessWidget {
  final AgentIdentity identity;

  const _AgentHeader({required this.identity});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(QuorumSpacing.md, QuorumSpacing.md, QuorumSpacing.md, QuorumSpacing.sm),
      child: Row(
        children: [
          const AgentBadge(agent: QuorumAgent.calendar, compact: true),
          const SizedBox(width: QuorumSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(identity.name, style: Theme.of(context).textTheme.headlineSmall?.copyWith(color: QuorumDarkGround.textPrimary)),
                Text(identity.purpose, style: Theme.of(context).textTheme.bodySmall?.copyWith(color: QuorumDarkGround.textSecondary)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _EmptyBody extends StatelessWidget {
  final bool permissionGranted;
  final AgentIdentity identity;

  const _EmptyBody({required this.permissionGranted, required this.identity});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _AgentHeader(identity: identity),
        Expanded(
          child: Center(
            child: HonestEmptyState(
              icon: permissionGranted ? Icons.event_available_outlined : Icons.lock_outline_rounded,
              headline: permissionGranted ? 'No upcoming events' : 'Calendar access not granted',
              detail: permissionGranted
                  ? 'Nothing in the next 14 days. Book one with the button below.'
                  : "Allow calendar access in your device Settings to see your real, upcoming events here.",
            ),
          ),
        ),
      ],
    );
  }
}

class _EventsBody extends StatelessWidget {
  final List<CalendarMirrorData> events;
  final DateTime now;
  final AgentIdentity identity;

  const _EventsBody({required this.events, required this.now, required this.identity});

  @override
  Widget build(BuildContext context) {
    final sorted = sortByStartTime(events);
    // Real Meeting-Load Defense -- the real, genuine multi-day
    // projection `backend/features/meeting_load.py`'s own docstring
    // named this exact screen as its intended home: real, on-device
    // synced events, pure and synchronous (no async fetch needed,
    // unlike `_PredictiveRiskBanner`'s own real live backend call --
    // this is genuinely local data already in hand).
    final weeklyLoad = computeWeeklyMeetingLoad(events, now: now);

    return ListView.builder(
      padding: const EdgeInsets.fromLTRB(QuorumSpacing.md, QuorumSpacing.md, QuorumSpacing.md, QuorumSpacing.xxl),
      itemCount: sorted.length + 2,
      itemBuilder: (context, index) {
        if (index == 0) return _AgentHeader(identity: identity);
        if (index == 1) return _MeetingLoadBanner(weeklyLoad: weeklyLoad, now: now, accent: identity.accent);
        final event = sorted[index - 2];
        return Padding(
          padding: const EdgeInsets.only(top: QuorumSpacing.sm),
          child: _EventRow(event: event, now: now, accent: identity.accent),
        );
      },
    );
  }
}

class _EventRow extends StatelessWidget {
  final CalendarMirrorData event;
  final DateTime now;
  final Color accent;

  const _EventRow({required this.event, required this.now, required this.accent});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(QuorumSpacing.md),
      decoration: solidPanelDecoration(accent: accent),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: accent.withValues(alpha: 0.14),
              shape: BoxShape.circle,
              border: Border.all(color: accent.withValues(alpha: 0.4)),
            ),
            child: Icon(Icons.event_outlined, size: 18, color: accent),
          ),
          const SizedBox(width: QuorumSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(event.title, style: Theme.of(context).textTheme.titleSmall?.copyWith(color: QuorumDarkGround.textPrimary)),
                const SizedBox(height: 2),
                Text(formatEventTimeRange(event.startTime, event.endTime), style: QuorumMono.detail(context)),
              ],
            ),
          ),
          const SizedBox(width: QuorumSpacing.sm),
          Text(formatEventDayLabel(event.startTime, now), style: QuorumMono.label(context, color: accent)),
        ],
      ),
    );
  }
}

/// A real, deliberately quiet summary of the next 7 real days' own
/// real meeting load, matching `_PredictiveRiskBanner`'s own
/// established restraint (`tasks_screen.dart`): a real, honest
/// reassurance when nothing's overloaded, never a fabricated warning,
/// and a real, specific list of which real days look overloaded
/// otherwise -- never a bare "some days are busy."
///
/// Phase 8 Session 4 (`DEC-158`): the overloaded state signals through
/// a `StatusPill` in `QuorumDarkStatus.critical` (a real, quantified
/// negative outcome), never color alone.
class _MeetingLoadBanner extends StatelessWidget {
  final List<DailyMeetingLoad> weeklyLoad;
  final DateTime now;
  final Color accent;

  const _MeetingLoadBanner({required this.weeklyLoad, required this.now, required this.accent});

  @override
  Widget build(BuildContext context) {
    final overloadedDays = weeklyLoad.where((d) => d.state.isOverloaded).toList();

    return Padding(
      padding: const EdgeInsets.only(bottom: QuorumSpacing.sm),
      child: GlassPanel(
        accent: overloadedDays.isEmpty ? accent : QuorumDarkStatus.critical,
        accentStrength: overloadedDays.isEmpty ? 0.4 : 1.0,
        child: overloadedDays.isEmpty
            ? Row(
                children: [
                  const Icon(Icons.check_circle_outline_rounded, size: 18, color: QuorumDarkStatus.verified),
                  const SizedBox(width: QuorumSpacing.sm),
                  Expanded(
                    child: Text('Next 7 days look manageable.', style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: QuorumDarkGround.textPrimary)),
                  ),
                ],
              )
            : Row(
                children: [
                  const Icon(Icons.warning_amber_rounded, size: 18, color: QuorumDarkStatus.critical),
                  const SizedBox(width: QuorumSpacing.sm),
                  Expanded(
                    child: Text(
                      'Heavier than usual: ${overloadedDays.map((d) => formatEventDayLabel(d.day, now)).join(', ')}',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: QuorumDarkGround.textPrimary),
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}
