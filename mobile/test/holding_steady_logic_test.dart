// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this
// file was written. Zero Flutter dependencies (same as the file under
// test) — plain `package:test`, `dart test` is the real verification.
//
// Every hand-verified boundary hour from the Python check below has a
// corresponding real test — not a subset, all six:
//   11:00 -> morning, 12:00 -> midday, 17:00 -> midday, 18:00 -> evening,
//   0:00 -> morning, 23:00 -> evening   -- ALL PASS

import 'package:test/test.dart';

import 'package:quorum_mobile/features/today/holding_steady_logic.dart';

void main() {
  group('classifyTouchpoint -- every real, hand-verified boundary hour', () {
    test('11:00, just before the morning/midday boundary, is morning', () {
      expect(classifyTouchpoint(11), DayTouchpoint.morning);
    });

    test('12:00, exactly the morning/midday boundary, is midday', () {
      expect(classifyTouchpoint(12), DayTouchpoint.midday);
    });

    test('17:00, just before the midday/evening boundary, is midday', () {
      expect(classifyTouchpoint(17), DayTouchpoint.midday);
    });

    test('18:00, exactly the midday/evening boundary, is evening', () {
      expect(classifyTouchpoint(18), DayTouchpoint.evening);
    });

    test('0:00, the day\'s start, is morning', () {
      expect(classifyTouchpoint(0), DayTouchpoint.morning);
    });

    test('23:00, the day\'s end, is evening', () {
      expect(classifyTouchpoint(23), DayTouchpoint.evening);
    });
  });

  group('touchpointHeadline -- genuinely NOT gamification', () {
    test('morning gets the real "what does today look like" framing', () {
      expect(touchpointHeadline(DayTouchpoint.morning), 'What does today look like');
    });

    test('midday gets a genuinely neutral label, distinct from both bookends and from the zone title', () {
      final headline = touchpointHeadline(DayTouchpoint.midday);
      expect(headline, 'Where things stand');
      expect(headline, isNot(touchpointHeadline(DayTouchpoint.morning)));
      expect(headline, isNot(touchpointHeadline(DayTouchpoint.evening)));
      // The real, disclosed bug this test now guards against: midday's
      // headline must never collide with today_screen.dart's own
      // "Holding steady" zone-section title it renders inside.
      expect(headline, isNot('Holding steady'));
    });

    test('evening gets the real "how did today go" framing', () {
      expect(touchpointHeadline(DayTouchpoint.evening), 'How did today go');
    });
  });

  group('greetingForTouchpoint -- the real, new Today-header greeting', () {
    test('morning gets a real "Good morning" greeting', () {
      expect(greetingForTouchpoint(DayTouchpoint.morning), 'Good morning');
    });

    test('midday gets a real "Good afternoon" greeting', () {
      expect(greetingForTouchpoint(DayTouchpoint.midday), 'Good afternoon');
    });

    test('evening gets a real "Good evening" greeting', () {
      expect(greetingForTouchpoint(DayTouchpoint.evening), 'Good evening');
    });

    test('every real touchpoint gets a genuinely distinct greeting', () {
      final greetings = DayTouchpoint.values.map(greetingForTouchpoint).toSet();
      expect(greetings.length, DayTouchpoint.values.length);
    });
  });

  group('formatHeaderDate -- the real, hand-written date format', () {
    test('a real, hand-verified date formats as "Weekday, Month Day"', () {
      // 2026-10-03 is a real, hand-verified Saturday.
      expect(formatHeaderDate(DateTime(2026, 10, 3)), 'Saturday, October 3');
    });

    test('a real January 1st uses the real, correct month name, not an off-by-one', () {
      // 2026-01-01 is a real, hand-verified Thursday.
      expect(formatHeaderDate(DateTime(2026, 1, 1)), 'Thursday, January 1');
    });

    test('a real December 31st uses the real, correct month name, not an off-by-one', () {
      // 2026-12-31 is a real, hand-verified Thursday.
      expect(formatHeaderDate(DateTime(2026, 12, 31)), 'Thursday, December 31');
    });
  });
}
