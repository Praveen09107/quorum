// Real tests for features/gate_showcase/gate_showcase_logic.dart
// (`DEC-193`). Zero Flutter dependency -- `dart test` is the real
// verification.

import 'package:test/test.dart';

import 'package:quorum_mobile/features/gate_showcase/gate_showcase_logic.dart';

void main() {
  group('GateValidatorData.fromJson', () {
    test('parses a real wired validator', () {
      final validator = GateValidatorData.fromJson({
        'name': 'DeadlineConflictCheck',
        'function_name': 'deadline_conflict_check',
        'description': 'Checks for a scheduling conflict.',
        'evidence_source': 'calendar_events table',
        'wired': true,
      });
      expect(validator.name, 'DeadlineConflictCheck');
      expect(validator.wired, isTrue);
    });
  });

  group('GateStatsData.fromJson', () {
    test('parses real stakes_counts and keeps null fields honestly null', () {
      final stats = GateStatsData.fromJson({
        'total_resolved': 3,
        'stakes_counts': {'S1': 2, 'S3': 1},
        'success_count': 2,
        'caught_count': 1,
        'rejected_count': 0,
        'uncertain_count': 0,
        'catch_rate': 0.333,
        'rows_with_recorded_timeline': 1,
        'stage_b_ran_count': 1,
        'revised_count': 0,
        'quota_used': 11,
        'quota_limit': 20,
      });
      expect(stats.stakesCounts, {'S1': 2, 'S3': 1});
      expect(stats.catchRate, 0.333);
      expect(stats.quotaUsed, 11);
    });
  });

  group('formatGateCatchRate', () {
    test('an honest sentence, never a fabricated percentage, when catchRate is null', () {
      expect(formatGateCatchRate(null), 'No resolved actions yet');
    });

    test('rounds a real rate to a whole percent', () {
      expect(formatGateCatchRate(0.667), '67%');
    });
  });

  group('describeQuotaHeadroom', () {
    test('an honest unavailable message when either field is null', () {
      expect(describeQuotaHeadroom(null, 20), 'Quota headroom unavailable right now');
      expect(describeQuotaHeadroom(11, null), 'Quota headroom unavailable right now');
    });

    test('a real remaining count when both are present', () {
      expect(describeQuotaHeadroom(11, 20), '9 of 20 Gemini calls left today');
    });
  });

  group('stageBInvocationRate', () {
    test('null, honestly, when no row has ever recorded a timeline', () {
      const stats = GateStatsData(
        totalResolved: 2,
        stakesCounts: {},
        successCount: 2,
        caughtCount: 0,
        rejectedCount: 0,
        uncertainCount: 0,
        catchRate: 0.0,
        rowsWithRecordedTimeline: 0,
        stageBRanCount: 0,
        revisedCount: 0,
        quotaUsed: null,
        quotaLimit: null,
      );
      expect(stageBInvocationRate(stats), isNull);
    });

    test('a real fraction when at least one row has a recorded timeline', () {
      const stats = GateStatsData(
        totalResolved: 2,
        stakesCounts: {},
        successCount: 2,
        caughtCount: 0,
        rejectedCount: 0,
        uncertainCount: 0,
        catchRate: 0.0,
        rowsWithRecordedTimeline: 2,
        stageBRanCount: 1,
        revisedCount: 0,
        quotaUsed: null,
        quotaLimit: null,
      );
      expect(stageBInvocationRate(stats), 0.5);
    });
  });
}
