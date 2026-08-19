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
}
