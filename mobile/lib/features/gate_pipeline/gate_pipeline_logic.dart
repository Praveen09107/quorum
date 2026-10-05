// Pure logic for the live Gate pipeline (`DEC-189` Block B).
//
// Zero Flutter imports, deliberately -- everything here is parsing and
// reduction, so it runs under plain `dart test` and is the part of this
// feature that carries real test coverage. The widget layer renders what
// this produces and makes no decisions of its own.
//
// WHAT THIS FEATURE IS FOR. `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md`
// §12.1 names the interaction this product should own: "a verification
// check resolving is a real, literal, satisfying interaction, not a
// metaphor buried in copy." Nothing in this app had ever shown the Gate
// working -- every screen rendered a finished verdict, which is the
// diagnosed cause of the real complaint that the app does not feel like
// an agentic AI app. `POST /capture/stream` emits each pipeline stage as
// it genuinely completes; this file turns that stream into something a
// screen can draw.
//
// THE HONESTY RULE THIS FILE ENFORCES, and the reason the reducer is
// shaped the way it is: a pending row is only ever created for a stage
// the SERVER has said is coming. The `routing` event reports the real
// Stage A check count and whether Stage B and the Critic will run, so
// placeholder rows are grounded in a real server-reported fact rather
// than an optimistic guess about what the Gate is probably going to do.
// Before `routing` arrives, no Stage A rows exist at all.

import 'dart:convert';

/// One real event decoded from the stream.
class GateEvent {
  final String name;

  /// Milliseconds from the start of the whole pipeline (including
  /// extraction), as measured server-side. Absent on the terminal
  /// `result`/`error` events, which are not timed stages.
  final int? atMs;

  /// How long this stage itself took, server-measured. Absent on
  /// `*.start` markers, which record a beginning rather than a span.
  final int? durationMs;

  final Map<String, dynamic> data;

  const GateEvent({required this.name, this.atMs, this.durationMs, required this.data});

  /// Parses one `data:` payload. Throws [FormatException] on anything
  /// that is not a JSON object carrying an `event` name -- a malformed
  /// frame is a real protocol error and must not be silently turned
  /// into an empty event that renders as a blank row.
  factory GateEvent.fromJson(String raw) {
    final decoded = jsonDecode(raw);
    if (decoded is! Map<String, dynamic>) {
      throw const FormatException('Gate event payload was not a JSON object');
    }
    final name = decoded['event'];
    if (name is! String || name.isEmpty) {
      throw const FormatException('Gate event payload carried no event name');
    }
    return GateEvent(
      name: name,
      atMs: _asInt(decoded['at_ms']),
      durationMs: _asInt(decoded['duration_ms']),
      data: decoded,
    );
  }

  static int? _asInt(Object? value) {
    if (value is int) return value;
    if (value is num) return value.round();
    return null;
  }
}

/// A stateful parser for real Server-Sent Events framing.
///
/// Stateful because it must be: an HTTP response arrives in arbitrary
/// chunks, and a chunk boundary can fall anywhere -- including in the
/// middle of a JSON payload or between the two newlines that terminate a
/// frame. A stateless "split each chunk on blank lines" parser works
/// right up until a frame straddles a chunk, then silently corrupts it.
/// This holds a buffer and only emits complete frames.
class SseFrameParser {
  final StringBuffer _buffer = StringBuffer();

  /// Feeds one chunk and returns every COMPLETE frame payload it
  /// completed, in order. Comment lines (`:` keepalives) are dropped --
  /// they exist only to hold the connection open through a long
  /// extraction call and carry nothing to render.
  List<String> addChunk(String chunk) {
    _buffer.write(chunk);
    final text = _buffer.toString();

    // A frame ends at a blank line. Normalise CRLF first: the spec
    // permits either, and a proxy may rewrite line endings in transit.
    final normalised = text.replaceAll('\r\n', '\n');
    final parts = normalised.split('\n\n');

    // The final part is either an incomplete frame or an empty string
    // after a clean boundary -- either way it stays buffered.
    final trailing = parts.removeLast();
    _buffer
      ..clear()
      ..write(trailing);

    final payloads = <String>[];
    for (final frame in parts) {
      final data = _dataFrom(frame);
      if (data != null) payloads.add(data);
    }
    return payloads;
  }

  /// Extracts the `data:` content from one frame, or null for a comment
  /// or an empty frame. Multiple `data:` lines in one frame are joined
  /// with a newline, per the SSE spec -- this server sends one line, but
  /// honouring the spec costs nothing and means a future change on
  /// either side cannot silently truncate a payload.
  static String? _dataFrom(String frame) {
    final lines = frame.split('\n');
    final dataLines = <String>[];
    for (final line in lines) {
      final trimmed = line.trimRight();
      if (trimmed.isEmpty || trimmed.startsWith(':')) continue;
      if (trimmed.startsWith('data:')) {
        dataLines.add(trimmed.substring('data:'.length).trimLeft());
      }
      // Any other field (`event:`, `id:`, `retry:`) is deliberately
      // ignored rather than treated as an error -- this server does not
      // send them, and a conformant client must tolerate them.
    }
    if (dataLines.isEmpty) return null;
    return dataLines.join('\n');
  }
}

/// What kind of pipeline stage a row represents -- drives its icon and
/// accent in the UI.
enum PipelineRowKind { understanding, routing, stageACheck, critic, judge, revision, done }

/// A row's resolved state. [noData] is a genuinely distinct third
/// evidence value, never collapsed into pass or fail -- the same
/// three-valued discipline the backend's own `Finding.evidence_state`
/// holds. [pending] is a FOURTH, structurally different thing: "has not
/// reported yet," which is a transport fact rather than a finding.
enum PipelineRowStatus { pending, verified, contradicted, noData, neutral, failed }

/// One row in the live pipeline timeline.
class PipelineRow {
  /// Stable across rebuilds, so a pending row animating into a resolved
  /// one is the same widget rather than a replacement. Without this,
  /// every incoming event would restart every row's animation.
  final String id;

  final PipelineRowKind kind;
  final String label;

  /// The human-readable substance of this row -- a validator's real
  /// claim, the Critic's real objection summary, the Judge's real
  /// decision. Null while pending.
  final String? detail;

  final PipelineRowStatus status;
  final int? durationMs;
  final int? atMs;

  /// Which Stage A pass this came from. Only meaningful above 1, which
  /// happens when the Gate re-ran Stage A against a payload its own
  /// Judge had revised -- a genuinely different thing from the first
  /// pass and labelled as such.
  final int? round;

  const PipelineRow({
    required this.id,
    required this.kind,
    required this.label,
    required this.status,
    this.detail,
    this.durationMs,
    this.atMs,
    this.round,
  });

  bool get isPending => status == PipelineRowStatus.pending;

  PipelineRow copyWith({
    String? label,
    String? detail,
    PipelineRowStatus? status,
    int? durationMs,
    int? atMs,
    int? round,
  }) {
    return PipelineRow(
      id: id,
      kind: kind,
      label: label ?? this.label,
      detail: detail ?? this.detail,
      status: status ?? this.status,
      durationMs: durationMs ?? this.durationMs,
      atMs: atMs ?? this.atMs,
      round: round ?? this.round,
    );
  }
}

/// The real revision diff: what the Judge changed, and what it was
/// before. The single most compelling artifact this product can show --
/// "here is what the AI wanted to do, and here is what the Gate made it
/// change" -- which was unshowable until migration `0021` stopped
/// discarding the pre-revision payload.
class RevisionSummary {
  final List<String> changedKeys;

  const RevisionSummary({required this.changedKeys});
}

/// A terminal failure reported in-band on the stream.
///
/// In-band because an SSE response commits to `200 OK` the moment its
/// first byte is sent, so a failure discovered after streaming begins
/// cannot be an HTTP status. The server still sends the status it WOULD
/// have returned, which is what [status] carries.
class PipelineError {
  final int? status;
  final String detail;

  const PipelineError({required this.detail, this.status});
}

/// Everything a screen needs to draw the pipeline at one moment.
class LivePipelineView {
  final List<PipelineRow> rows;

  /// The real stakes tier, once routing has been announced.
  final String? stakes;
  final String? actionType;

  final RevisionSummary? revision;

  /// The real final capture result, as the ordinary `/quick_capture`
  /// response shape. Present only once the pipeline genuinely finished.
  final Map<String, dynamic>? result;

  final PipelineError? error;

  /// Server-measured total, from the last timed event. Deliberately not
  /// measured client-side: a client-side timer would include network
  /// latency and render time and then present the sum as if it were the
  /// pipeline's own cost.
  final int? totalMs;

  const LivePipelineView({
    required this.rows,
    this.stakes,
    this.actionType,
    this.revision,
    this.result,
    this.error,
    this.totalMs,
  });

  static const LivePipelineView empty = LivePipelineView(rows: []);

  bool get isFinished => result != null || error != null;
  bool get isRunning => !isFinished;
}

/// Reduces the real event stream into a view.
///
/// A pure function over the whole event list rather than an incremental
/// mutable reducer, deliberately: a capture emits a small, bounded
/// number of events (a handful of markers plus one per validator), so
/// re-reducing on each event is genuinely cheap, and a pure function is
/// testable by writing down a list of events and asserting the result.
LivePipelineView reducePipelineEvents(List<GateEvent> events) {
  final rows = <String, PipelineRow>{};
  String? stakes;
  String? actionType;
  RevisionSummary? revision;
  Map<String, dynamic>? result;
  PipelineError? error;
  int? totalMs;

  void put(PipelineRow row) => rows[row.id] = row;

  for (final event in events) {
    if (event.atMs != null) {
      totalMs = event.atMs;
    }

    switch (event.name) {
      case 'understanding.start':
        put(PipelineRow(
          id: 'understanding',
          kind: PipelineRowKind.understanding,
          label: 'Understanding what you wrote',
          status: PipelineRowStatus.pending,
          atMs: event.atMs,
        ));

      case 'understanding':
        final fields = _stringList(event.data['extracted_fields']);
        final domain = event.data['domain'] as String?;
        put(PipelineRow(
          id: 'understanding',
          kind: PipelineRowKind.understanding,
          label: 'Understood',
          detail: _understandingDetail(domain, fields),
          status: PipelineRowStatus.verified,
          durationMs: event.durationMs,
          atMs: event.atMs,
        ));

      case 'routing':
        stakes = event.data['stakes'] as String?;
        actionType = event.data['action_type'] as String?;
        final stageBWillRun = event.data['stage_b_will_run'] == true;
        final criticWillRun = event.data['critic_will_run'] == true;
        put(PipelineRow(
          id: 'routing',
          kind: PipelineRowKind.routing,
          label: 'Stakes: ${stakes ?? 'unknown'}',
          detail: _routingDetail(stakes, stageBWillRun: stageBWillRun),
          status: PipelineRowStatus.neutral,
          atMs: event.atMs,
        ));
        // Placeholder rows for stages the SERVER has said are coming --
        // never speculative. Stage A's individual validator identities
        // are not known until each one reports, so these are indexed
        // placeholders that each resolve in place.
        final checkCount = GateEvent._asInt(event.data['stage_a_check_count']) ?? 0;
        for (var i = 0; i < checkCount; i++) {
          final id = _checkId(1, i);
          if (!rows.containsKey(id)) {
            put(PipelineRow(
              id: id,
              kind: PipelineRowKind.stageACheck,
              label: 'Verification check ${i + 1}',
              status: PipelineRowStatus.pending,
              round: 1,
            ));
          }
        }
        if (criticWillRun) {
          put(const PipelineRow(
            id: 'critic',
            kind: PipelineRowKind.critic,
            label: 'Critic review',
            status: PipelineRowStatus.pending,
          ));
        }
        if (stageBWillRun) {
          put(const PipelineRow(
            id: 'judge',
            kind: PipelineRowKind.judge,
            label: 'Judge decision',
            status: PipelineRowStatus.pending,
          ));
        }

      case 'stage_a.start':
        final round = GateEvent._asInt(event.data['round']) ?? 1;
        final checkCount = GateEvent._asInt(event.data['check_count']) ?? 0;
        // A second round means the Gate revised the payload and is
        // re-checking it. Those are genuinely new rows, not updates to
        // the first round's, so a user can see both passes.
        if (round > 1) {
          for (var i = 0; i < checkCount; i++) {
            put(PipelineRow(
              id: _checkId(round, i),
              kind: PipelineRowKind.stageACheck,
              label: 'Re-checking ${i + 1}',
              status: PipelineRowStatus.pending,
              round: round,
            ));
          }
        }

      case 'stage_a.check':
        final round = GateEvent._asInt(event.data['round']) ?? 1;
        final index = GateEvent._asInt(event.data['index']) ?? rows.length;
        put(PipelineRow(
          id: _checkId(round, index),
          kind: PipelineRowKind.stageACheck,
          label: event.data['validator'] as String? ?? 'Verification check',
          detail: event.data['claim'] as String?,
          status: statusForEvidence(event.data['evidence_state'] as String?),
          durationMs: event.durationMs,
          atMs: event.atMs,
          round: round,
        ));

      case 'stage_a.check_error':
        final round = GateEvent._asInt(event.data['round']) ?? 1;
        final index = GateEvent._asInt(event.data['index']) ?? 0;
        put(PipelineRow(
          id: _checkId(round, index),
          kind: PipelineRowKind.stageACheck,
          label: 'Verification check failed',
          detail: 'The check could not run (${event.data['error'] ?? 'unknown error'}).',
          status: PipelineRowStatus.failed,
          durationMs: event.durationMs,
          atMs: event.atMs,
          round: round,
        ));

      case 'stage_b.critic.start':
        put(const PipelineRow(
          id: 'critic',
          kind: PipelineRowKind.critic,
          label: 'Critic reviewing',
          status: PipelineRowStatus.pending,
        ));

      case 'stage_b.critic':
        final objections = GateEvent._asInt(event.data['objection_count']) ?? 0;
        put(PipelineRow(
          id: 'critic',
          kind: PipelineRowKind.critic,
          label: 'Critic',
          detail: _criticDetail(objections, event.data['highest_severity'] as String?),
          // An objection raised is not a failure -- it is the Critic
          // doing its job. Neutral either way; the Judge decides.
          status: objections == 0 ? PipelineRowStatus.verified : PipelineRowStatus.neutral,
          durationMs: event.durationMs,
          atMs: event.atMs,
        ));

      case 'stage_b.critic.error':
        put(PipelineRow(
          id: 'critic',
          kind: PipelineRowKind.critic,
          label: 'Critic unavailable',
          detail: 'The Critic could not be reached (${event.data['error'] ?? 'unknown error'}).',
          status: PipelineRowStatus.failed,
          durationMs: event.durationMs,
          atMs: event.atMs,
        ));

      case 'stage_b.judge.start':
        put(const PipelineRow(
          id: 'judge',
          kind: PipelineRowKind.judge,
          label: 'Judge deciding',
          status: PipelineRowStatus.pending,
        ));

      case 'stage_b.judge':
        final decision = event.data['decision'] as String?;
        put(PipelineRow(
          id: 'judge',
          kind: PipelineRowKind.judge,
          label: 'Judge',
          detail: _decisionDetail(decision, revised: event.data['revised'] == true),
          status: _statusForDecision(decision),
          durationMs: event.durationMs,
          atMs: event.atMs,
        ));

      case 'stage_b.judge.error':
        put(PipelineRow(
          id: 'judge',
          kind: PipelineRowKind.judge,
          label: 'Judge unavailable',
          detail: 'The Judge could not be reached (${event.data['error'] ?? 'unknown error'}).',
          status: PipelineRowStatus.failed,
          durationMs: event.durationMs,
          atMs: event.atMs,
        ));

      case 'revision':
        final changed = _stringList(event.data['changed_keys']);
        revision = RevisionSummary(changedKeys: changed);
        put(PipelineRow(
          id: 'revision',
          kind: PipelineRowKind.revision,
          label: 'The Gate corrected this',
          detail: _revisionDetail(changed),
          status: PipelineRowStatus.neutral,
          atMs: event.atMs,
        ));

      case 'done':
        final decision = event.data['decision'] as String?;
        put(PipelineRow(
          id: 'done',
          kind: PipelineRowKind.done,
          label: _doneLabel(decision),
          detail: _doneDetail(event.data),
          status: _statusForDecision(decision),
          atMs: event.atMs,
        ));

      case 'result':
        result = Map<String, dynamic>.from(event.data)..remove('event');
        // Any row still pending when the pipeline finished genuinely
        // never reported. Marking it `failed` would assert it failed;
        // leaving it spinning forever would be worse. `noData` is the
        // honest state -- we do not know what it found, because it
        // never said.
        for (final entry in rows.entries.toList()) {
          if (entry.value.isPending) {
            rows[entry.key] = entry.value.copyWith(
              label: entry.value.label,
              detail: 'This step never reported a result.',
              status: PipelineRowStatus.noData,
            );
          }
        }

      case 'error':
        error = PipelineError(
          detail: event.data['detail'] as String? ?? 'Something went wrong.',
          status: GateEvent._asInt(event.data['status']),
        );
        for (final entry in rows.entries.toList()) {
          if (entry.value.isPending) {
            rows[entry.key] = entry.value.copyWith(
              detail: 'Stopped before this step completed.',
              status: PipelineRowStatus.noData,
            );
          }
        }
    }
  }

  return LivePipelineView(
    rows: rows.values.toList(),
    stakes: stakes,
    actionType: actionType,
    revision: revision,
    result: result,
    error: error,
    totalMs: totalMs,
  );
}

/// Maps the real three-valued `evidence_state` to a row status.
///
/// An unrecognised value resolves to [PipelineRowStatus.noData], never
/// [PipelineRowStatus.verified] -- the same fail-safe direction
/// `gate_reveal_logic.dart::visualStateForEvidence()` already
/// establishes. Presenting an unknown state as a pass is the one
/// genuinely dangerous direction to be wrong in.
PipelineRowStatus statusForEvidence(String? evidenceState) {
  switch (evidenceState) {
    case 'verified_true':
      return PipelineRowStatus.verified;
    case 'verified_false':
      return PipelineRowStatus.contradicted;
    case 'no_data_found':
      return PipelineRowStatus.noData;
    default:
      return PipelineRowStatus.noData;
  }
}

String _checkId(int round, int index) => 'check-r$round-i$index';

String _understandingDetail(String? domain, List<String> fields) {
  // Deliberately describes WHICH fields were extracted, not their
  // values: the values are untrusted model output and already reach the
  // user through the real result, while "it understood this as an email
  // with a recipient and an intent" is the genuinely useful fact here.
  final named = fields.where((f) => f != 'domain' && f != 'operation').toList();
  if (domain == null) return 'Read your text.';
  if (named.isEmpty) return 'Read this as a $domain request.';
  return 'Read this as a $domain request, picking out ${named.join(', ')}.';
}

String _routingDetail(String? stakes, {required bool stageBWillRun}) {
  final tier = switch (stakes) {
    'S0' => 'No real-world effect',
    'S1' => 'Reversible, so no second opinion is needed',
    'S2' => 'Significant, so a Judge reviews it',
    'S3' => 'Irreversible, so a Critic and a Judge both review it, and you approve it',
    _ => 'Stakes could not be determined',
  };
  if (!stageBWillRun) return '$tier -- code checks only.';
  return tier;
}

String _criticDetail(int objections, String? highestSeverity) {
  if (objections == 0) return 'Reviewed and signed off with no objections.';
  final severity = highestSeverity == null ? '' : ', highest severity $highestSeverity';
  return 'Raised $objections objection${objections == 1 ? '' : 's'}$severity.';
}

String _decisionDetail(String? decision, {required bool revised}) {
  final base = switch (decision) {
    'approve' => 'Approved',
    'reject' => 'Rejected',
    'revise' => 'Sent back for a correction',
    'escalate_to_human' => 'Escalated to you',
    _ => 'Decision: ${decision ?? 'unknown'}',
  };
  return revised ? '$base, after correcting the payload' : base;
}

String _revisionDetail(List<String> changedKeys) {
  if (changedKeys.isEmpty) return 'The Gate changed the action before approving it.';
  return 'Changed ${changedKeys.join(', ')} before approving.';
}

String _doneLabel(String? decision) {
  return switch (decision) {
    'approve' => 'Approved',
    'reject' => 'Rejected',
    'revise' => 'Needs a correction',
    'escalate_to_human' => 'Waiting for you',
    _ => 'Finished',
  };
}

String _doneDetail(Map<String, dynamic> data) {
  final parts = <String>[];
  final findings = GateEvent._asInt(data['finding_count']);
  if (findings != null) {
    parts.add('$findings check${findings == 1 ? '' : 's'}');
  }
  if (data['stage_b_ran'] == true) {
    parts.add('Stage B ran');
  } else {
    parts.add('Stage B not needed');
  }
  final revisions = GateEvent._asInt(data['revision_count']);
  if (revisions != null && revisions > 0) {
    parts.add('$revisions correction');
  }
  return parts.join(' - ');
}

PipelineRowStatus _statusForDecision(String? decision) {
  return switch (decision) {
    'approve' => PipelineRowStatus.verified,
    'reject' => PipelineRowStatus.contradicted,
    // A revise or an escalation is neither a pass nor a failure -- the
    // Gate did its job and the action needs something more. Collapsing
    // either into a failure would misrepresent what happened.
    'revise' => PipelineRowStatus.neutral,
    'escalate_to_human' => PipelineRowStatus.neutral,
    _ => PipelineRowStatus.neutral,
  };
}

List<String> _stringList(Object? value) {
  if (value is! List) return const [];
  return value.whereType<String>().toList();
}
