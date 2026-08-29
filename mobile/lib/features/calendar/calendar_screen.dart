import 'package:flutter/material.dart';

import 'package:quorum_mobile/db/database.dart';
import 'package:quorum_mobile/features/calendar/calendar_logic.dart';
import 'package:quorum_mobile/features/meeting_load/meeting_load_logic.dart';
import 'package:quorum_mobile/theme/quorum_theme.dart';
import 'package:quorum_mobile/theme/spacing.dart';

/// A real, deliberately minimal display of whatever's currently in the
/// real, on-device `CalendarMirror` table (`db/database.dart`) -- this
/// screen itself never touches the `device_calendar` plugin, permission,
/// or sync at all; it's a pure, testable read of already-fetched data,
/// the same separation-of-concerns `calendar_sync.dart` itself already
/// establishes between the real sync logic and the plugin call.
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
    if (events.isEmpty && !permissionGranted) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(QuorumSpacing.lg),
          child: Text(
            "Quorum doesn't have permission to read your calendar yet. "
            'Allow calendar access in your device Settings to see your real, upcoming events here.',
            textAlign: TextAlign.center,
          ),
        ),
      );
    }

    if (events.isEmpty) {
      return const Center(child: Text('No upcoming events in the next 14 days.'));
    }

    final sorted = sortByStartTime(events);

    // Real Meeting-Load Defense -- the real, genuine multi-day
    // projection `backend/features/meeting_load.py`'s own docstring
    // named this exact screen as its intended home: real, on-device
    // synced events, pure and synchronous (no async fetch needed,
    // unlike `_PredictiveRiskBanner`'s own real live backend call --
    // this is genuinely local data already in hand).
    final weeklyLoad = computeWeeklyMeetingLoad(events, now: now);

    return ListView.builder(
      padding: const EdgeInsets.all(QuorumSpacing.md),
      itemCount: sorted.length + 1,
      itemBuilder: (context, index) {
        if (index == 0) return _MeetingLoadBanner(weeklyLoad: weeklyLoad, now: now);
        final event = sorted[index - 1];
        return Padding(
          padding: const EdgeInsets.only(top: QuorumSpacing.sm),
          child: Card(
            child: ListTile(
              leading: QuorumIconBadge(
                icon: Icons.event_outlined,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
              title: Text(event.title),
              subtitle: Text(formatEventTimeRange(event.startTime, event.endTime)),
              trailing: Text(formatEventDayLabel(event.startTime, now)),
            ),
          ),
        );
      },
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
/// Phase 8 Session 4 (`DEC-158`): the overloaded state now signals
/// through a `QuorumIconBadge` in `QuorumStatusColors.critical` (a real,
/// quantified negative outcome, matching the same corrected precedent
/// `tasks_screen.dart`'s own Predictive Risk banner already established
/// in `DEC-157`'s own review), rather than flipping the whole Card's
/// background to `errorContainer` -- consistent with every other real
/// status signal in this app, "badge carries the meaning, card stays
/// neutral."
class _MeetingLoadBanner extends StatelessWidget {
  final List<DailyMeetingLoad> weeklyLoad;
  final DateTime now;

  const _MeetingLoadBanner({required this.weeklyLoad, required this.now});

  @override
  Widget build(BuildContext context) {
    final overloadedDays = weeklyLoad.where((d) => d.state.isOverloaded).toList();

    if (overloadedDays.isEmpty) {
      return const Card(
        child: ListTile(
          leading: QuorumIconBadge(icon: Icons.check_circle_outline, color: QuorumStatusColors.verified),
          title: Text('Next 7 days look manageable.'),
        ),
      );
    }

    final dayLabels = overloadedDays.map((d) => formatEventDayLabel(d.day, now)).join(', ');
    return Card(
      child: ListTile(
        leading: const QuorumIconBadge(icon: Icons.warning_amber_rounded, color: QuorumStatusColors.critical),
        title: Text('Heavier than usual: $dayLabels'),
      ),
    );
  }
}
