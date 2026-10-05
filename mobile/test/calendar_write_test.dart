// Real tests for the calendar-write pure logic added to
// features/calendar_sync.dart (`DEC-191`, product rebuild Block C).
//
// `pickWritableCalendar` itself never touches the plugin (plain
// `Calendar` data objects in, a plain `Calendar?` out) -- but
// `package:device_calendar/device_calendar.dart`'s own barrel file
// imports Flutter transitively (confirmed directly after `dart test`
// failed to load this file with Flutter-internal switch-exhaustiveness
// errors), so this file needs `flutter test`, not plain `dart test`,
// despite the function under test having no real Flutter dependency
// of its own.

import 'package:device_calendar/device_calendar.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:quorum_mobile/features/calendar_sync.dart';

Calendar _calendar({required String id, bool? isReadOnly, bool? isDefault}) {
  final calendar = Calendar();
  calendar.id = id;
  calendar.isReadOnly = isReadOnly;
  calendar.isDefault = isDefault;
  return calendar;
}

void main() {
  group('pickWritableCalendar', () {
    test('prefers the real default calendar when it is writable', () {
      final calendars = [
        _calendar(id: 'work', isReadOnly: false, isDefault: false),
        _calendar(id: 'personal', isReadOnly: false, isDefault: true),
      ];
      expect(pickWritableCalendar(calendars)!.id, 'personal');
    });

    test('falls back to the first writable calendar when the default is read-only', () {
      // The common real case: an organization-managed work calendar is
      // often set as the device default AND synced read-only.
      final calendars = [
        _calendar(id: 'work-readonly-default', isReadOnly: true, isDefault: true),
        _calendar(id: 'personal', isReadOnly: false, isDefault: false),
      ];
      expect(pickWritableCalendar(calendars)!.id, 'personal');
    });

    test('returns null when every real calendar on the device is read-only', () {
      // An honest "nowhere to write this," never a crash or a silent
      // wrong choice.
      final calendars = [
        _calendar(id: 'a', isReadOnly: true),
        _calendar(id: 'b', isReadOnly: true),
      ];
      expect(pickWritableCalendar(calendars), isNull);
    });

    test('returns null for an empty calendar list', () {
      expect(pickWritableCalendar([]), isNull);
    });

    test('treats a null isReadOnly as writable, matching the plugin\'s own optional field', () {
      final calendars = [_calendar(id: 'unspecified', isReadOnly: null)];
      expect(pickWritableCalendar(calendars)!.id, 'unspecified');
    });

    test('skips a calendar with no real id, even if otherwise writable', () {
      final noId = Calendar()..isReadOnly = false;
      final withId = _calendar(id: 'real', isReadOnly: false);
      expect(pickWritableCalendar([noId, withId])!.id, 'real');
    });
  });
}
