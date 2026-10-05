// Real tests for the live Gate pipeline's pure logic (`DEC-189` Block
// B). Zero Flutter dependency -- matches gate_reveal_logic_test.dart's
// own established pattern exactly: plain `package:test`, `dart test` is
// the real verification.

import 'package:test/test.dart';
import 'package:quorum_mobile/features/gate_pipeline/gate_pipeline_logic.dart';

GateEvent _event(String name, [Map<String, dynamic> data = const {}]) {
  return GateEvent.fromJson('{"event":"$name"${_encodeExtra(data)}}');
}

String _encodeExtra(Map<String, dynamic> data) {
  if (data.isEmpty) return '';
  final parts = data.entries.map((e) {
    final value = e.value;
    if (value is String) return '"${e.key}":"$value"';
    if (value is List) return '"${e.key}":[${value.map((v) => '"$v"').join(',')}]';
    return '"${e.key}":$value';
  });
  return ',${parts.join(',')}';
}

void main() {
  group('SseFrameParser', () {
    test('parses complete frames from a single chunk', () {
      final parser = SseFrameParser();
      final payloads = parser.addChunk('data: {"a":1}\n\ndata: {"b":2}\n\n');
      expect(payloads, ['{"a":1}', '{"b":2}']);
    });

    test('holds an incomplete frame until the rest of it arrives', () {
      // THE reason this parser is stateful. A chunk boundary can fall
      // anywhere, including mid-JSON. A stateless "split on blank
      // lines" parser works until a frame straddles a chunk, then
      // silently corrupts it.
      final parser = SseFrameParser();
      expect(parser.addChunk('data: {"ev'), isEmpty);
      expect(parser.addChunk('ent":"x"}'), isEmpty);
      expect(parser.addChunk('\n\n'), ['{"event":"x"}']);
    });

    test('splits a frame boundary that itself straddles two chunks', () {
      final parser = SseFrameParser();
      expect(parser.addChunk('data: {"a":1}\n'), isEmpty);
      expect(parser.addChunk('\ndata: {"b":2}\n\n'), ['{"a":1}', '{"b":2}']);
    });

    test('drops keepalive comment lines', () {
      // Keepalives exist only to hold the connection open through a
      // long extraction call. They carry nothing to render, and must
      // never surface as an empty event that draws a blank row.
      final parser = SseFrameParser();
      final payloads = parser.addChunk(': keepalive\n\ndata: {"event":"done"}\n\n');
      expect(payloads, ['{"event":"done"}']);
    });

    test('normalises CRLF, which a proxy may introduce in transit', () {
      final parser = SseFrameParser();
      expect(parser.addChunk('data: {"a":1}\r\n\r\n'), ['{"a":1}']);
    });

    test('ignores other SSE fields rather than failing on them', () {
      final parser = SseFrameParser();
      final payloads = parser.addChunk('id: 7\nevent: ping\ndata: {"a":1}\nretry: 100\n\n');
      expect(payloads, ['{"a":1}']);
    });

    test('joins multiple data lines in one frame, per the SSE spec', () {
      final parser = SseFrameParser();
      expect(parser.addChunk('data: line1\ndata: line2\n\n'), ['line1\nline2']);
    });
  });

  group('GateEvent', () {
    test('parses a real event with its timings', () {
      final event = GateEvent.fromJson('{"event":"stage_a.check","at_ms":120,"duration_ms":3,"validator":"x"}');
      expect(event.name, 'stage_a.check');
      expect(event.atMs, 120);
      expect(event.durationMs, 3);
      expect(event.data['validator'], 'x');
    });

    test('rejects a payload with no event name rather than inventing one', () {
      // A malformed frame is a real protocol error. Silently becoming an
      // unnamed event would draw a blank row and look like a Gate bug.
      expect(() => GateEvent.fromJson('{"at_ms":1}'), throwsFormatException);
      expect(() => GateEvent.fromJson('{"event":""}'), throwsFormatException);
      expect(() => GateEvent.fromJson('[]'), throwsFormatException);
    });
  });

  group('statusForEvidence', () {
    test('maps the three real evidence states to three distinct statuses', () {
      expect(statusForEvidence('verified_true'), PipelineRowStatus.verified);
      expect(statusForEvidence('verified_false'), PipelineRowStatus.contradicted);
      expect(statusForEvidence('no_data_found'), PipelineRowStatus.noData);
    });

    test('an unrecognised state resolves to noData, never verified', () {
      // Presenting an unknown state as a pass is the one genuinely
      // dangerous direction to be wrong in -- same fail-safe direction
      // `gate_reveal_logic.dart` already establishes.
      expect(statusForEvidence('some_future_state'), PipelineRowStatus.noData);
      expect(statusForEvidence(null), PipelineRowStatus.noData);
      expect(statusForEvidence('some_future_state'), isNot(PipelineRowStatus.verified));
    });
  });

  group('reducePipelineEvents', () {
    test('an empty stream produces an empty, still-running view', () {
      final view = reducePipelineEvents([]);
      expect(view.rows, isEmpty);
      expect(view.isRunning, isTrue);
      expect(view.isFinished, isFalse);
    });

    test('creates no Stage A rows before routing has announced them', () {
      // The honesty rule this reducer enforces: a pending row only ever
      // exists for a stage the SERVER said is coming. Guessing how many
      // checks will run would show a user a pipeline the Gate never
      // promised.
      final view = reducePipelineEvents([
        _event('understanding.start'),
        _event('understanding', {'domain': 'tasks', 'extracted_fields': ['title']}),
      ]);
      expect(view.rows.where((r) => r.kind == PipelineRowKind.stageACheck), isEmpty);
    });

    test('routing creates exactly the pending rows the server reported', () {
      final view = reducePipelineEvents([
        _event('routing', {
          'action_type': 'send_email',
          'stakes': 'S3',
          'stage_b_will_run': true,
          'critic_will_run': true,
          'stage_a_check_count': 3,
        }),
      ]);

      expect(view.stakes, 'S3');
      expect(view.actionType, 'send_email');
      final checks = view.rows.where((r) => r.kind == PipelineRowKind.stageACheck).toList();
      expect(checks.length, 3);
      expect(checks.every((r) => r.isPending), isTrue);
      expect(view.rows.any((r) => r.kind == PipelineRowKind.critic), isTrue);
      expect(view.rows.any((r) => r.kind == PipelineRowKind.judge), isTrue);
    });

    test('S1 routing creates no Critic or Judge rows at all', () {
      // S1 genuinely never reaches Stage B. Rendering a pending Judge
      // row that resolves to nothing would imply a step was skipped or
      // failed, when in truth it was never going to run.
      final view = reducePipelineEvents([
        _event('routing', {
          'action_type': 'create_task',
          'stakes': 'S1',
          'stage_b_will_run': false,
          'critic_will_run': false,
          'stage_a_check_count': 1,
        }),
      ]);

      expect(view.rows.any((r) => r.kind == PipelineRowKind.critic), isFalse);
      expect(view.rows.any((r) => r.kind == PipelineRowKind.judge), isFalse);
      expect(view.rows.firstWhere((r) => r.kind == PipelineRowKind.routing).detail, contains('code checks only'));
    });

    test('a resolving check replaces its own pending row in place', () {
      // Same stable id, so the row animates from pending to resolved
      // rather than being torn down and rebuilt -- which would restart
      // every other row's animation on every incoming event.
      final view = reducePipelineEvents([
        _event('routing', {'stakes': 'S1', 'stage_b_will_run': false, 'critic_will_run': false, 'stage_a_check_count': 2}),
        _event('stage_a.check', {
          'round': 1,
          'index': 0,
          'validator': 'provenance_check',
          'claim': 'Justification is user-originated',
          'evidence_state': 'verified_true',
          'duration_ms': 1,
        }),
      ]);

      final checks = view.rows.where((r) => r.kind == PipelineRowKind.stageACheck).toList();
      expect(checks.length, 2, reason: 'resolving a check must not add a row');
      final resolved = checks.firstWhere((r) => !r.isPending);
      expect(resolved.label, 'provenance_check');
      expect(resolved.detail, 'Justification is user-originated');
      expect(resolved.status, PipelineRowStatus.verified);
      expect(resolved.durationMs, 1);
    });

    test('a second Stage A round adds new rows rather than overwriting the first', () {
      // A second round means the Gate revised the payload and re-checked
      // it. Overwriting round 1 would hide that the Gate corrected
      // itself, which is the most interesting thing it ever does.
      final view = reducePipelineEvents([
        _event('routing', {'stakes': 'S3', 'stage_b_will_run': true, 'critic_will_run': true, 'stage_a_check_count': 1}),
        _event('stage_a.check', {'round': 1, 'index': 0, 'validator': 'a', 'claim': 'c1', 'evidence_state': 'verified_true'}),
        _event('stage_a.start', {'round': 2, 'check_count': 1}),
        _event('stage_a.check', {'round': 2, 'index': 0, 'validator': 'a', 'claim': 'c2', 'evidence_state': 'verified_true'}),
      ]);

      final checks = view.rows.where((r) => r.kind == PipelineRowKind.stageACheck).toList();
      expect(checks.length, 2);
      expect(checks.map((r) => r.round).toSet(), {1, 2});
      expect(checks.map((r) => r.detail).toSet(), {'c1', 'c2'});
    });

    test('a Critic objection is neutral, not a failure', () {
      // The Critic raising an objection is it doing its job. Styling
      // that as a failure would misrepresent the architecture -- the
      // Judge is what decides.
      final view = reducePipelineEvents([
        _event('stage_b.critic', {'objection_count': 2, 'highest_severity': 'high', 'signed_off_count': 0}),
      ]);
      final critic = view.rows.firstWhere((r) => r.kind == PipelineRowKind.critic);
      expect(critic.status, PipelineRowStatus.neutral);
      expect(critic.detail, contains('2 objections'));
      expect(critic.detail, contains('high'));
    });

    test('a Critic sign-off with no objections reads as verified', () {
      final view = reducePipelineEvents([
        _event('stage_b.critic', {'objection_count': 0, 'signed_off_count': 1}),
      ]);
      final critic = view.rows.firstWhere((r) => r.kind == PipelineRowKind.critic);
      expect(critic.status, PipelineRowStatus.verified);
      expect(critic.detail, contains('no objections'));
    });

    test('a revision produces the real changed-key diff row', () {
      final view = reducePipelineEvents([
        _event('revision', {'changed_keys': ['body', 'subject']}),
      ]);
      expect(view.revision, isNotNull);
      expect(view.revision!.changedKeys, ['body', 'subject']);
      final row = view.rows.firstWhere((r) => r.kind == PipelineRowKind.revision);
      expect(row.detail, contains('body'));
      expect(row.detail, contains('subject'));
    });

    test('revise and escalate are neutral, never failures', () {
      for (final decision in ['revise', 'escalate_to_human']) {
        final view = reducePipelineEvents([_event('done', {'decision': decision})]);
        final done = view.rows.firstWhere((r) => r.kind == PipelineRowKind.done);
        expect(done.status, PipelineRowStatus.neutral, reason: '$decision must not read as a failure');
      }
    });

    test('a result marks any still-pending row as noData, never as passed or failed', () {
      // A step that never reported is genuinely unknown. Marking it
      // failed would assert it failed; leaving it spinning forever is
      // worse; calling it verified would be a lie.
      final view = reducePipelineEvents([
        _event('routing', {'stakes': 'S1', 'stage_b_will_run': false, 'critic_will_run': false, 'stage_a_check_count': 2}),
        _event('stage_a.check', {'round': 1, 'index': 0, 'validator': 'a', 'claim': 'c', 'evidence_state': 'verified_true'}),
        _event('result', {'decision': 'approve', 'domain': 'tasks'}),
      ]);

      expect(view.isFinished, isTrue);
      expect(view.result!['decision'], 'approve');
      expect(view.result!.containsKey('event'), isFalse, reason: 'the envelope key must not leak into the result');
      final stranded = view.rows.firstWhere((r) => r.id == 'check-r1-i1');
      expect(stranded.status, PipelineRowStatus.noData);
      expect(stranded.detail, contains('never reported'));
    });

    test('an in-band error is surfaced with the status the server would have returned', () {
      // An SSE response commits to 200 on its first byte, so a later
      // failure can only be reported in-band. The server still sends
      // the status it would have used, and a client needs it.
      final view = reducePipelineEvents([
        _event('routing', {'stakes': 'S2', 'stage_b_will_run': true, 'critic_will_run': false, 'stage_a_check_count': 1}),
        _event('error', {'status': 503, 'detail': 'The Gate reviewer is temporarily unavailable.'}),
      ]);

      expect(view.isFinished, isTrue);
      expect(view.error!.status, 503);
      expect(view.error!.detail, contains('temporarily unavailable'));
      expect(view.rows.where((r) => r.isPending), isEmpty, reason: 'nothing may still spin after a terminal error');
    });

    test('totalMs comes from the last server-timed event, never measured client-side', () {
      // A client-side timer would include network latency and render
      // time, then present the sum as the pipeline's own cost.
      final view = reducePipelineEvents([
        _event('understanding', {'at_ms': 7817, 'duration_ms': 7817}),
        _event('done', {'at_ms': 7819, 'decision': 'approve'}),
      ]);
      expect(view.totalMs, 7819);
    });

    test('reduces a full, realistic S3 stream end to end', () {
      final view = reducePipelineEvents([
        _event('understanding.start', {'at_ms': 0}),
        _event('understanding', {'at_ms': 4200, 'duration_ms': 4200, 'domain': 'email', 'extracted_fields': ['recipient_email', 'user_intent']}),
        _event('routing', {
          'at_ms': 4201,
          'action_type': 'send_email',
          'stakes': 'S3',
          'stage_b_will_run': true,
          'critic_will_run': true,
          'stage_a_check_count': 1,
        }),
        _event('stage_a.start', {'at_ms': 4201, 'round': 1, 'check_count': 1}),
        _event('stage_a.check', {'at_ms': 4202, 'duration_ms': 1, 'round': 1, 'index': 0, 'validator': 'provenance_check', 'claim': 'User-originated', 'evidence_state': 'verified_true'}),
        _event('stage_b.critic.start', {'at_ms': 4202}),
        _event('stage_b.critic', {'at_ms': 5100, 'duration_ms': 898, 'objection_count': 1, 'signed_off_count': 0, 'highest_severity': 'medium'}),
        _event('stage_b.judge.start', {'at_ms': 5100}),
        _event('stage_b.judge', {'at_ms': 6400, 'duration_ms': 1300, 'decision': 'approve', 'revised': true}),
        _event('revision', {'at_ms': 6400, 'changed_keys': ['body']}),
        _event('done', {'at_ms': 6405, 'decision': 'approve', 'stakes': 'S3', 'revision_count': 1, 'stage_b_ran': true, 'finding_count': 1}),
        _event('result', {'decision': 'approve', 'domain': 'email', 'executed': false}),
      ]);

      expect(view.isFinished, isTrue);
      expect(view.stakes, 'S3');
      expect(view.rows.where((r) => r.isPending), isEmpty);
      expect(view.revision!.changedKeys, ['body']);
      expect(view.totalMs, 6405);

      final judge = view.rows.firstWhere((r) => r.kind == PipelineRowKind.judge);
      expect(judge.detail, contains('after correcting'));

      final done = view.rows.firstWhere((r) => r.kind == PipelineRowKind.done);
      expect(done.label, 'Approved');
      expect(done.detail, contains('Stage B ran'));
      expect(done.detail, contains('1 correction'));

      // Every row carries a stable id, which is what keeps animations
      // attached to the right row across rebuilds.
      expect(view.rows.map((r) => r.id).toSet().length, view.rows.length);
    });

    test('an S3 routing detail names the human-approval requirement', () {
      // S3 always requires explicit human approval, in every mode, no
      // exception -- the single hardest rule in this architecture. The
      // UI must say so at the moment routing happens, not only at the
      // end.
      final view = reducePipelineEvents([
        _event('routing', {'stakes': 'S3', 'stage_b_will_run': true, 'critic_will_run': true, 'stage_a_check_count': 1}),
      ]);
      final routing = view.rows.firstWhere((r) => r.kind == PipelineRowKind.routing);
      expect(routing.detail, contains('you approve'));
    });
  });
}
