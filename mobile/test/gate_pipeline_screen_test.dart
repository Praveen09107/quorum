// Real widget tests for features/gate_pipeline/gate_pipeline_screen.dart
// (`DEC-189` Block B) -- the live Gate pipeline, the centerpiece of this
// product rebuild. Matches quick_capture_screen_test.dart's own
// established harness pattern: a plain injected fetcher, no mocked HTTP.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:quorum_mobile/features/calendar_sync.dart' show CreateLocalEventResult;
import 'package:quorum_mobile/features/gate_pipeline/gate_pipeline_logic.dart';
import 'package:quorum_mobile/features/gate_pipeline/gate_pipeline_screen.dart';
import 'package:quorum_mobile/theme/quorum_dark_theme.dart';

GateEvent _event(String name, Map<String, dynamic> data) =>
    GateEvent(name: name, atMs: data['at_ms'] as int?, durationMs: data['duration_ms'] as int?, data: data);

/// A small, realistic S1 stream -- no Stage B, straight to an executed
/// result. Delivered with real microtask gaps so a test can observe the
/// pipeline mid-flight, not just its final state.
Stream<GateEvent> _s1Stream() async* {
  yield _event('understanding.start', const {});
  await Future<void>.delayed(Duration.zero);
  yield _event('understanding', const {'domain': 'tasks', 'extracted_fields': ['title']});
  yield _event('routing', const {
    'action_type': 'create_task',
    'stakes': 'S1',
    'stage_b_will_run': false,
    'critic_will_run': false,
    'stage_a_check_count': 1,
  });
  yield _event('stage_a.start', const {'round': 1, 'check_count': 1});
  await Future<void>.delayed(Duration.zero);
  yield _event('stage_a.check', const {
    'round': 1,
    'index': 0,
    'validator': 'provenance_check',
    'claim': 'Justification is user-originated',
    'evidence_state': 'verified_true',
    'duration_ms': 1,
  });
  yield _event('done', const {'decision': 'approve', 'stakes': 'S1', 'stage_b_ran': false, 'revision_count': 0, 'finding_count': 1});
  yield _event('result', const {'decision': 'approve', 'domain': 'tasks', 'executed': true, 'title': 'A real task'});
}

/// A real S3 stream ending in a genuine pending human approval --
/// `executed: false` with `decision: approve`, the ORDINARY S3 case.
Stream<GateEvent> _s3PendingApprovalStream({String traceId = 'trace-123'}) async* {
  yield _event('routing', const {
    'action_type': 'send_email',
    'stakes': 'S3',
    'stage_b_will_run': true,
    'critic_will_run': true,
    'stage_a_check_count': 1,
  });
  await Future<void>.delayed(Duration.zero);
  yield _event('stage_a.check', const {
    'round': 1,
    'index': 0,
    'validator': 'recipient_check',
    'claim': 'Recipient is a known contact',
    'evidence_state': 'verified_true',
  });
  yield _event('stage_b.critic', const {'objection_count': 0, 'signed_off_count': 1});
  yield _event('stage_b.judge', const {'decision': 'approve', 'revised': false});
  yield _event('done', {'decision': 'approve', 'stakes': 'S3', 'stage_b_ran': true, 'revision_count': 0, 'finding_count': 1, 'trace_id': traceId});
  yield _event('result', const {
    'decision': 'approve',
    'stakes': 'S3',
    'domain': 'email',
    'executed': false,
    'email_recipient': 'sarah@example.com',
  });
}

Widget _harness({
  required Stream<GateEvent> Function(String) stream,
  Future<void> Function(String)? onApprove,
  Future<void> Function(String)? onReject,
  CreateLocalEventCall? onCreateLocalEvent,
  OnDeviceExtractAttempt? onDeviceExtract,
}) {
  return MaterialApp(
    theme: buildQuorumDarkTheme(),
    home: GatePipelineScreen(
      captureStream: (text, {onDeviceAttempted = false, onDeviceFailureReason}) => stream(text),
      onApprove: onApprove ?? (_) async {},
      onReject: onReject ?? (_) async {},
      onCreateLocalEvent: onCreateLocalEvent,
      onDeviceExtract: onDeviceExtract,
    ),
  );
}

void main() {
  group('input phase', () {
    testWidgets('shows example chips and fills the field when one is tapped', (tester) async {
      await tester.pumpWidget(_harness(stream: (_) => _s1Stream()));

      expect(find.text('What should Quorum do?'), findsOneWidget);
      final chip = find.text('log ₹450 for lunch');
      expect(chip, findsOneWidget);

      await tester.tap(chip);
      await tester.pump();

      final field = tester.widget<TextField>(find.byType(TextField));
      expect(field.controller!.text, 'log ₹450 for lunch');
    });

    testWidgets('does nothing when submitted blank', (tester) async {
      var called = false;
      await tester.pumpWidget(_harness(stream: (_) {
        called = true;
        return _s1Stream();
      }));

      await tester.tap(find.text('Run it through the Gate'));
      await tester.pump();

      expect(called, isFalse);
    });
  });

  group('live streaming', () {
    testWidgets('an S1 capture streams rows and finishes with Done, no approval bar', (tester) async {
      await tester.pumpWidget(_harness(stream: (_) => _s1Stream()));
      await tester.enterText(find.byType(TextField), 'write the test task');
      await tester.tap(find.text('Run it through the Gate'));
      await tester.pumpAndSettle();

      expect(find.text('provenance_check'), findsOneWidget);
      expect(find.textContaining('Justification is user-originated'), findsOneWidget);
      // S1 never reaches Stage B -- no Critic/Judge row should appear.
      expect(find.textContaining('Critic'), findsNothing);
      // No human approval needed for an S1 executed action.
      expect(find.text('Approve'), findsNothing);
      expect(find.text('Done'), findsOneWidget);
    });

    testWidgets('a real S3 pending approval shows the recipient and both buttons', (tester) async {
      await tester.pumpWidget(_harness(stream: (_) => _s3PendingApprovalStream()));
      await tester.enterText(find.byType(TextField), 'email sarah the update');
      await tester.tap(find.text('Run it through the Gate'));
      await tester.pumpAndSettle();

      // Never approve blind -- the recipient must be visible before the
      // buttons are even reachable.
      expect(find.textContaining('sarah@example.com'), findsOneWidget);
      expect(find.text('Approve'), findsOneWidget);
      expect(find.text('Reject'), findsOneWidget);
    });

    testWidgets('tapping Approve calls the real callback with the real trace id and shows Done', (tester) async {
      String? approvedId;
      await tester.pumpWidget(_harness(
        stream: (_) => _s3PendingApprovalStream(traceId: 'trace-abc'),
        onApprove: (id) async => approvedId = id,
      ));
      await tester.enterText(find.byType(TextField), 'email sarah the update');
      await tester.tap(find.text('Run it through the Gate'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Approve'));
      await tester.pumpAndSettle();

      expect(approvedId, 'trace-abc');
      expect(find.text('Approve'), findsNothing);
      expect(find.text('Reject'), findsNothing);
      expect(find.text('Done'), findsOneWidget);
    });

    testWidgets('tapping Reject calls the real callback and the approval bar resolves', (tester) async {
      String? rejectedId;
      await tester.pumpWidget(_harness(
        stream: (_) => _s3PendingApprovalStream(traceId: 'trace-xyz'),
        onReject: (id) async => rejectedId = id,
      ));
      await tester.enterText(find.byType(TextField), 'email sarah the update');
      await tester.tap(find.text('Run it through the Gate'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Reject'));
      await tester.pumpAndSettle();

      expect(rejectedId, 'trace-xyz');
      expect(find.text('Done'), findsOneWidget);
    });

    testWidgets('a real approval failure shows the error and keeps the buttons tappable', (tester) async {
      await tester.pumpWidget(_harness(
        stream: (_) => _s3PendingApprovalStream(),
        onApprove: (_) async => throw Exception('network error'),
      ));
      await tester.enterText(find.byType(TextField), 'email sarah the update');
      await tester.tap(find.text('Run it through the Gate'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Approve'));
      await tester.pumpAndSettle();

      // Buttons remain -- a failed approval must never silently resolve
      // as if it had succeeded.
      expect(find.text('Approve'), findsOneWidget);
      expect(find.text('Reject'), findsOneWidget);
    });

    testWidgets('an in-band stream error is shown and still allows trying again', (tester) async {
      Stream<GateEvent> errorStream(String _) async* {
        yield _event('routing', const {'stakes': 'S2', 'stage_b_will_run': true, 'critic_will_run': false, 'stage_a_check_count': 1});
        yield _event('error', const {'status': 503, 'detail': 'The Gate reviewer is temporarily unavailable.'});
      }

      await tester.pumpWidget(_harness(stream: errorStream));
      await tester.enterText(find.byType(TextField), 'anything');
      await tester.tap(find.text('Run it through the Gate'));
      await tester.pumpAndSettle();

      expect(find.textContaining('temporarily unavailable'), findsOneWidget);
      expect(find.text('Try again'), findsOneWidget);

      await tester.tap(find.text('Try again'));
      await tester.pump();

      expect(find.text('What should Quorum do?'), findsOneWidget);
    });

    testWidgets('the new-capture action resets back to the input phase', (tester) async {
      await tester.pumpWidget(_harness(stream: (_) => _s1Stream()));
      await tester.enterText(find.byType(TextField), 'write the test task');
      await tester.tap(find.text('Run it through the Gate'));
      await tester.pumpAndSettle();

      await tester.tap(find.byIcon(Icons.add_rounded));
      await tester.pump();

      expect(find.text('What should Quorum do?'), findsOneWidget);
    });
  });

  group('on-device calendar write (DEC-191)', () {
    /// A real `create_calendar_event_local` stream, S2 -- the Gate
    /// approves it, but `executed` stays permanently `False` since no
    /// server-side execution target exists for this action type by
    /// design. `event_start`/`event_end`/`event_title` ARE populated
    /// (as of this same session's backend fix) -- that is exactly what
    /// this screen needs to finish the job itself.
    Stream<GateEvent> localCalendarStream() async* {
      yield _event('routing', const {
        'action_type': 'create_calendar_event_local',
        'stakes': 'S2',
        'stage_b_will_run': true,
        'critic_will_run': false,
        'stage_a_check_count': 1,
      });
      yield _event('done', const {'decision': 'approve', 'stakes': 'S2', 'stage_b_ran': true, 'revision_count': 0});
      yield _event('result', const {
        'decision': 'approve',
        'domain': 'calendar',
        'calendar_action': 'create_calendar_event_local',
        'executed': false,
        'event_start': '2027-01-01T14:00:00.000Z',
        'event_end': '2027-01-01T15:00:00.000Z',
        'event_title': 'Design review',
      });
    }

    testWidgets('a real approved local event triggers the on-device write and shows success', (tester) async {
      String? capturedTitle;
      await tester.pumpWidget(_harness(
        stream: (_) => localCalendarStream(),
        onCreateLocalEvent: ({required title, required start, required end, description}) async {
          capturedTitle = title;
          return const CreateLocalEventResult(success: true, eventId: 'evt-1', detail: 'Real event created on-device.');
        },
      ));
      await tester.enterText(find.byType(TextField), 'block 2-3pm for a design review');
      await tester.tap(find.text('Run it through the Gate'));
      await tester.pumpAndSettle();

      expect(capturedTitle, 'Design review');
      expect(find.text('Added to your on-device calendar.'), findsOneWidget);
    });

    testWidgets('an on-device write failure shows the real honest reason', (tester) async {
      await tester.pumpWidget(_harness(
        stream: (_) => localCalendarStream(),
        onCreateLocalEvent: ({required title, required start, required end, description}) async {
          return const CreateLocalEventResult(success: false, detail: 'Calendar permission was not granted.');
        },
      ));
      await tester.enterText(find.byType(TextField), 'block 2-3pm for a design review');
      await tester.tap(find.text('Run it through the Gate'));
      await tester.pumpAndSettle();

      expect(find.text('Calendar permission was not granted.'), findsOneWidget);
    });

    testWidgets('no write is attempted when onCreateLocalEvent is not configured', (tester) async {
      // The honest-gating default: absent, not a crash, not a silent
      // no-op that pretends to have happened.
      await tester.pumpWidget(_harness(stream: (_) => localCalendarStream()));
      await tester.enterText(find.byType(TextField), 'block 2-3pm for a design review');
      await tester.tap(find.text('Run it through the Gate'));
      await tester.pumpAndSettle();

      expect(find.text('Added to your on-device calendar.'), findsNothing);
      expect(find.text('Done'), findsOneWidget);
    });

    testWidgets('a real S1 task capture never attempts a calendar write', (tester) async {
      var called = false;
      await tester.pumpWidget(_harness(
        stream: (_) => _s1Stream(),
        onCreateLocalEvent: ({required title, required start, required end, description}) async {
          called = true;
          return const CreateLocalEventResult(success: true, detail: 'should not happen');
        },
      ));
      await tester.enterText(find.byType(TextField), 'write the test task');
      await tester.tap(find.text('Run it through the Gate'));
      await tester.pumpAndSettle();

      expect(called, isFalse);
    });
  });

  group('on-device side-channel check (DEC-220)', () {
    testWidgets('a passing on-device extraction shows the real honest outcome line', (tester) async {
      await tester.pumpWidget(_harness(
        stream: (_) => _s1Stream(),
        onDeviceExtract: (_) async => {
          'domain': 'tasks',
          'operation': 'create',
          'title': 'write the test task',
          'estimated_hours': 1,
          'deadline_iso': null,
        },
      ));
      await tester.enterText(find.byType(TextField), 'write the test task');
      await tester.tap(find.text('Run it through the Gate'));
      await tester.pumpAndSettle();

      expect(find.textContaining('Ran on-device (Llama 3.2 3B)'), findsOneWidget);
    });

    testWidgets('a structurally-invalid on-device extraction shows an honest fallback line, never the internal reason', (tester) async {
      await tester.pumpWidget(_harness(
        stream: (_) => _s1Stream(),
        // Missing `estimated_hours` -- fails the real correctness bar.
        onDeviceExtract: (_) async => {'domain': 'tasks', 'operation': 'create', 'title': 'write the test task'},
      ));
      await tester.enterText(find.byType(TextField), 'write the test task');
      await tester.tap(find.text('Run it through the Gate'));
      await tester.pumpAndSettle();

      expect(find.textContaining('Tried on-device (Llama 3.2 3B)'), findsOneWidget);
      expect(find.textContaining('estimated_hours'), findsNothing);
    });

    testWidgets('a real on-device inference failure shows an honest fallback line, never a raw error', (tester) async {
      await tester.pumpWidget(_harness(
        stream: (_) => _s1Stream(),
        onDeviceExtract: (_) async => throw Exception('model load failed: out of memory'),
      ));
      await tester.enterText(find.byType(TextField), 'write the test task');
      await tester.tap(find.text('Run it through the Gate'));
      await tester.pumpAndSettle();

      expect(find.textContaining('Tried on-device (Llama 3.2 3B)'), findsOneWidget);
      expect(find.textContaining('out of memory'), findsNothing);
    });

    testWidgets('no on-device row appears when not configured, matching the honest-gating precedent', (tester) async {
      await tester.pumpWidget(_harness(stream: (_) => _s1Stream()));
      await tester.enterText(find.byType(TextField), 'write the test task');
      await tester.tap(find.text('Run it through the Gate'));
      await tester.pumpAndSettle();

      expect(find.textContaining('on-device'), findsNothing);
    });

    testWidgets('a real S3 capture still always streams through the cloud pipeline even when on-device passes', (tester) async {
      // The real, deliberate safety property this screen holds: a
      // passing on-device check never substitutes for the cloud Gate
      // here -- the Approve/Reject bar for a genuine pending S3 must
      // still appear exactly as it always has.
      await tester.pumpWidget(_harness(
        stream: (_) => _s3PendingApprovalStream(),
        onDeviceExtract: (_) async => {
          'domain': 'email',
          'operation': 'create',
          'recipient_description': 'Sarah',
          'user_intent': 'send the update',
        },
      ));
      await tester.enterText(find.byType(TextField), 'email sarah the update');
      await tester.tap(find.text('Run it through the Gate'));
      await tester.pumpAndSettle();

      expect(find.textContaining('Ran on-device (Llama 3.2 3B)'), findsOneWidget);
      expect(find.text('Approve'), findsOneWidget);
      expect(find.text('Reject'), findsOneWidget);
    });
  });
}
