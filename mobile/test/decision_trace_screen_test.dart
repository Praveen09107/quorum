// Real widget tests for features/decision_trace/decision_trace_screen
// .dart (`DEC-201`, product rebuild).

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:quorum_mobile/api/action_status_api.dart';
import 'package:quorum_mobile/features/decision_trace/decision_trace_screen.dart';
import 'package:quorum_mobile/theme/quorum_dark_theme.dart';

ActionStatusData _data({
  String stakes = 'S1',
  String? outcome = 'approved_unchanged',
  List<dynamic>? timeline,
  Map<String, dynamic>? preRevisionPayload,
  Map<String, dynamic> payload = const {},
  Map<String, dynamic>? artifact,
}) {
  return ActionStatusData(
    proposalId: 'p1',
    actionType: 'create_email_draft',
    stakes: stakes,
    gateDecision: 'approve',
    outcome: outcome,
    createdAt: DateTime(2026, 10, 1, 12, 0),
    resolvedAt: DateTime(2026, 10, 1, 12, 0, 5),
    payload: payload,
    timeline: timeline,
    revisionCount: preRevisionPayload == null ? 0 : 1,
    preRevisionPayload: preRevisionPayload,
    artifact: artifact,
  );
}

Widget _harness(Future<ActionStatusData> Function(String) fetch) {
  return MaterialApp(
    theme: buildQuorumDarkTheme(),
    home: DecisionTraceScreen(proposalId: 'p1', fetch: fetch),
  );
}

void main() {
  testWidgets('renders the real action type, stakes, and outcome', (tester) async {
    await tester.pumpWidget(_harness((_) async => _data()));
    await tester.pumpAndSettle();

    expect(find.text('Create Email Draft'), findsOneWidget);
    expect(find.text('S1'), findsOneWidget);
    expect(find.text('Approved Unchanged'), findsOneWidget);
  });

  testWidgets('a real, null timeline (pre-dating recording) shows the honest "not recorded" state', (tester) async {
    await tester.pumpWidget(_harness((_) async => _data(timeline: null)));
    await tester.pumpAndSettle();

    expect(find.text('Not recorded for this action'), findsOneWidget);
  });

  testWidgets('a real, recorded timeline replays its real stage rows', (tester) async {
    final timeline = [
      {'event': 'routing', 'at_ms': 5, 'stakes': 'S1', 'action_type': 'create_task', 'stage_b_will_run': false, 'critic_will_run': false, 'stage_a_check_count': 1},
      {'event': 'stage_a.start', 'at_ms': 6, 'round': 1, 'check_count': 1},
      {'event': 'stage_a.check', 'at_ms': 10, 'duration_ms': 4, 'round': 1, 'index': 0, 'validator': 'ProvenanceCheck', 'claim': 'a real claim', 'evidence_state': 'verified_true', 'confidence': 0.9},
    ];
    await tester.pumpWidget(_harness((_) async => _data(timeline: timeline)));
    await tester.pumpAndSettle();

    expect(find.text('ProvenanceCheck'), findsOneWidget);
    expect(find.text('a real claim'), findsOneWidget);
  });

  testWidgets('a real revision diff shows the real before and after values, not just the changed key name', (tester) async {
    await tester.pumpWidget(_harness((_) async => _data(
          preRevisionPayload: {'amount': 60000.0},
          payload: {'amount': 55000.0},
          timeline: const [],
        )));
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(find.text('WHAT THE GATE CHANGED'), 300, scrollable: find.byType(Scrollable).first);
    expect(find.text('WHAT THE GATE CHANGED'), findsOneWidget);
    expect(find.text('amount'), findsOneWidget);
    expect(find.textContaining('Before: 60000.0'), findsOneWidget);
    expect(find.textContaining('After: 55000.0'), findsOneWidget);
  });

  testWidgets('a real revision record whose values genuinely did not change shows an honest, non-fabricated message', (tester) async {
    await tester.pumpWidget(_harness((_) async => _data(
          preRevisionPayload: {'amount': 55000.0},
          payload: {'amount': 55000.0},
          timeline: const [],
        )));
    await tester.pumpAndSettle();

    expect(find.text('The Judge reviewed this without changing it'), findsOneWidget);
  });

  testWidgets('no revision section appears at all when nothing was ever revised', (tester) async {
    await tester.pumpWidget(_harness((_) async => _data(preRevisionPayload: null, timeline: const [])));
    await tester.pumpAndSettle();

    expect(find.text('WHAT THE GATE CHANGED'), findsNothing);
  });

  testWidgets('a real artifact renders a real, tappable open link', (tester) async {
    await tester.pumpWidget(_harness((_) async => _data(
          artifact: {'message_id': 'm1', 'draft_id': 'd1'},
          timeline: const [],
        )));
    await tester.pumpAndSettle();

    expect(find.text('Open draft in Gmail'), findsOneWidget);
  });

  testWidgets('shows a real, honest error state on a real fetch failure, not a crash', (tester) async {
    await tester.pumpWidget(_harness((_) async => throw Exception('network down')));
    await tester.pumpAndSettle();

    expect(find.textContaining('network down'), findsOneWidget);
    expect(find.text('Try again'), findsOneWidget);
  });

  testWidgets('tapping Try again genuinely retries without throwing the real setState/Future assertion', (tester) async {
    var attempt = 0;
    await tester.pumpWidget(_harness((_) async {
      attempt++;
      if (attempt == 1) throw Exception('network down');
      return _data(timeline: const []);
    }));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Try again'));
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.text('Create Email Draft'), findsOneWidget);
  });
}
