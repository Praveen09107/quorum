import 'package:flutter/material.dart';

import 'package:quorum_mobile/db/database.dart';
import 'package:quorum_mobile/features/calendar/calendar_logic.dart';

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
          padding: EdgeInsets.all(24),
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

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: sorted.length,
      itemBuilder: (context, index) {
        final event = sorted[index];
        return Card(
          child: ListTile(
            leading: const Icon(Icons.event_outlined),
            title: Text(event.title),
            subtitle: Text(formatEventTimeRange(event.startTime, event.endTime)),
            trailing: Text(formatEventDayLabel(event.startTime, now)),
          ),
        );
      },
    );
  }
}
