// Real tests for features/agents/agents_logic.dart (`DEC-192`). Zero
// Flutter dependency -- `dart test` is the real verification.

import 'package:test/test.dart';
import 'package:quorum_mobile/features/agents/agents_logic.dart';

void main() {
  group('AgentStatsData.fromJson', () {
    test('parses a real, active agent', () {
      final stats = AgentStatsData.fromJson({
        'domain': 'email',
        'lifetime_actions': 10,
        'success_count': 7,
        'caught_count': 2,
        'rejected_count': 1,
        'uncertain_count': 0,
        'success_rate': 0.7,
        'last_activity': '2027-01-01T10:00:00+00:00',
      });
      expect(stats.domain, 'email');
      expect(stats.lifetimeActions, 10);
      expect(stats.successRate, 0.7);
      expect(stats.lastActivity, isNotNull);
      expect(stats.isActive, isTrue);
    });

    test('parses a genuinely inactive agent -- honest zeros, not placeholders', () {
      final stats = AgentStatsData.fromJson({
        'domain': 'career',
        'lifetime_actions': 0,
        'success_count': 0,
        'caught_count': 0,
        'rejected_count': 0,
        'uncertain_count': 0,
        'success_rate': null,
        'last_activity': null,
      });
      expect(stats.lifetimeActions, 0);
      expect(stats.successRate, isNull);
      expect(stats.lastActivity, isNull);
      expect(stats.isActive, isFalse);
    });
  });

  group('describeLastActivity', () {
    final now = DateTime.parse('2027-01-01T12:00:00Z');

    test('a real agent with no activity reads honestly, never a fabricated time', () {
      expect(describeLastActivity(null, now: now), 'No activity yet');
    });

    test('minutes, hours, days and weeks are each described distinctly', () {
      expect(describeLastActivity(now.subtract(const Duration(seconds: 30)), now: now), 'Just now');
      expect(describeLastActivity(now.subtract(const Duration(minutes: 5)), now: now), 'Active 5m ago');
      expect(describeLastActivity(now.subtract(const Duration(hours: 3)), now: now), 'Active 3h ago');
      expect(describeLastActivity(now.subtract(const Duration(days: 2)), now: now), 'Active 2d ago');
      expect(describeLastActivity(now.subtract(const Duration(days: 14)), now: now), 'Active 2w ago');
      expect(describeLastActivity(now.subtract(const Duration(days: 60)), now: now), 'Active over a month ago');
    });
  });

  group('describeSuccessRate', () {
    test('a real inactive agent never shows a fabricated rate', () {
      final stats = AgentStatsData.fromJson({
        'domain': 'career', 'lifetime_actions': 0, 'success_count': 0, 'caught_count': 0,
        'rejected_count': 0, 'uncertain_count': 0, 'success_rate': null, 'last_activity': null,
      });
      expect(describeSuccessRate(stats), 'No real actions yet');
    });

    test('an active agent with no resolvable rate (all uncertain) is honest, not a fabricated 0%', () {
      final stats = AgentStatsData.fromJson({
        'domain': 'email', 'lifetime_actions': 1, 'success_count': 0, 'caught_count': 0,
        'rejected_count': 0, 'uncertain_count': 1, 'success_rate': null, 'last_activity': '2027-01-01T00:00:00Z',
      });
      expect(describeSuccessRate(stats), 'Not enough resolved activity yet');
    });

    test('a real computed rate renders as a real rounded percentage', () {
      final stats = AgentStatsData.fromJson({
        'domain': 'tasks', 'lifetime_actions': 3, 'success_count': 2, 'caught_count': 1,
        'rejected_count': 0, 'uncertain_count': 0, 'success_rate': 0.667, 'last_activity': '2027-01-01T00:00:00Z',
      });
      expect(describeSuccessRate(stats), '67% approved unchanged');
    });
  });
}
