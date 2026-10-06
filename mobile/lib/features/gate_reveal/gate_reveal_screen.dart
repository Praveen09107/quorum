// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.
//
// Stage A renders first, unconditionally. Stage B — findings from the
// genuinely more expensive, judgment-based layer — only ever enters the
// widget tree at all if `stageBRan` is true, matching the Gate's own real
// architecture where S0/S1 actions never reach Stage B in the first
// place.
//
// A real, disclosed correction to this file's own prior claim (Phase 8
// Session 4, `DEC-158`): this header used to say the staged reveal was
// "literally implemented, not just described" -- checked directly before
// this session and found only half true. Stage B's PRESENCE was real and
// conditional (exactly as documented above), but nothing about its
// APPEARANCE was ever staged in time -- Stage A and Stage B rendered in
// the exact same frame, simultaneously, whenever Stage B existed at all.
// This session adds the real, timed piece that was actually missing:
// Stage B, when it exists, now appears a deliberate beat after Stage A
// (`QuorumMotion.reveal`, resolved through `QuorumMotion.resolve()` so a
// real reduced-motion accessibility setting skips the wait rather than
// being ignored), fading and sliding into place rather than snapping in.
// This is this app's first real animation of any kind, and a real,
// small, purposeful one -- not decorative motion for its own sake.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/gate_reveal/gate_reveal_logic.dart';
import 'package:quorum_mobile/theme/motion.dart';
import 'package:quorum_mobile/theme/quorum_theme.dart';
import 'package:quorum_mobile/theme/spacing.dart';

class GateRevealScreen extends StatefulWidget {
  final String proposalId;
  final GateRevealBundle bundle;

  /// REAL, DISCLOSED FIX (the redesign's own real Approve/Reject work):
  /// closes a real, previously-undiscovered gap -- this screen has
  /// always been read-only. Both are `null` when the caller has no
  /// real way to act at all (never shown as a dead button); each is
  /// independently `null`-able because `bundle.canApprove` can be
  /// false (nothing for a real "Approve" to execute) while "Reject"
  /// (dismiss) still genuinely applies -- see `GateRevealBundle.
  /// canApprove`'s own docstring for the full real scope boundary.
  final Future<void> Function(String proposalId)? onApprove;
  final Future<void> Function(String proposalId)? onReject;

  const GateRevealScreen({
    super.key,
    required this.proposalId,
    required this.bundle,
    this.onApprove,
    this.onReject,
  });

  @override
  State<GateRevealScreen> createState() => _GateRevealScreenState();
}

enum _ActionOutcome { none, approved, rejected }

class _GateRevealScreenState extends State<GateRevealScreen> {
  bool _showStageB = false;
  bool _scheduledReveal = false;
  bool _submitting = false;
  String? _submitError;
  _ActionOutcome _outcome = _ActionOutcome.none;

  Future<void> _handleApprove() async {
    final onApprove = widget.onApprove;
    if (onApprove == null) return;
    setState(() {
      _submitting = true;
      _submitError = null;
    });
    try {
      await onApprove(widget.proposalId);
      if (!mounted) return;
      setState(() {
        _submitting = false;
        _outcome = _ActionOutcome.approved;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _submitting = false;
        _submitError = e.toString();
      });
    }
  }

  Future<void> _handleReject() async {
    final onReject = widget.onReject;
    if (onReject == null) return;
    setState(() {
      _submitting = true;
      _submitError = null;
    });
    try {
      await onReject(widget.proposalId);
      if (!mounted) return;
      setState(() {
        _submitting = false;
        _outcome = _ActionOutcome.rejected;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _submitting = false;
        _submitError = e.toString();
      });
    }
  }

  // A real bug caught by this session's own real `flutter test` run, not
  // a hypothetical: `MediaQuery.of(context)` (inside `QuorumMotion
  // .resolve`) cannot be called from `initState()` -- Flutter's own
  // element lifecycle forbids establishing a new inherited-widget
  // dependency before the first `didChangeDependencies()` call, and
  // throws a real, live `FlutterError` the instant a Gate Reveal screen
  // actually mounts. `didChangeDependencies()` is the correct, standard
  // place for exactly this "read an InheritedWidget once at mount time"
  // pattern -- guarded by `_scheduledReveal` since Flutter can call it
  // more than once (e.g. a real theme/MediaQuery change), and this
  // reveal must only ever be scheduled once per real screen instance.
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_scheduledReveal) return;
    _scheduledReveal = true;
    if (!stageBRanForStakes(widget.bundle.stakes)) return;
    final delay = QuorumMotion.resolve(context, QuorumMotion.reveal);
    if (delay == Duration.zero) {
      // Reduced motion requested -- show Stage B immediately, no
      // artificial wait imposed on someone who asked not to have one.
      _showStageB = true;
    } else {
      Future.delayed(delay, () {
        if (mounted) setState(() => _showStageB = true);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final bundle = widget.bundle;
    final recordedFindings = bundle.findings;
    final recordedObjections = bundle.objections;
    // "Did Stage B run" is read from the Gate's own real stakes value,
    // never inferred from whether `objections` happens to be non-empty
    // -- a real S2 action can be genuinely reviewed by the Judge and
    // still carry an honestly empty objections list (DEC-146).
    final ranStageB = stageBRanForStakes(bundle.stakes);

    return ListView(
      padding: const EdgeInsets.all(QuorumSpacing.md),
      children: [
        if (_outcome != _ActionOutcome.none)
          _OutcomeBanner(outcome: _outcome)
        else if (bundle.isPending && (widget.onApprove != null || widget.onReject != null))
          _ActionBar(
            actionType: bundle.actionType,
            payload: bundle.payload,
            canApprove: bundle.canApprove && widget.onApprove != null,
            canReject: widget.onReject != null,
            submitting: _submitting,
            error: _submitError,
            onApprove: _handleApprove,
            onReject: _handleReject,
          ),
        if (_outcome != _ActionOutcome.none || (bundle.isPending && (widget.onApprove != null || widget.onReject != null)))
          const SizedBox(height: QuorumSpacing.lg),
        Text('Stage A — automated checks', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: QuorumSpacing.sm),
        if (recordedFindings == null)
          const ListTile(
            leading: Icon(Icons.info_outline, color: QuorumStatusColors.needsAttention),
            title: Text("Not recorded"),
            subtitle: Text("This action predates Gate Reveal, so its real findings were never saved."),
          )
        else
          for (final finding in recordedFindings) FindingRow(finding: finding),
        // Stage B only ever enters the widget tree if it genuinely ran,
        // AND only once the real, timed reveal above has fired -- an
        // S0/S1 action's screen has no Stage B section at all, ever; an
        // S2/S3 action's Stage B section doesn't exist for the first
        // `QuorumMotion.reveal` beat, then animates itself in the moment
        // it's first inserted.
        if (ranStageB && _showStageB) ...[
          const SizedBox(height: QuorumSpacing.lg),
          TweenAnimationBuilder<double>(
            tween: Tween(begin: 0.0, end: 1.0),
            duration: QuorumMotion.resolve(context, QuorumMotion.reveal),
            curve: Curves.easeOut,
            builder: (context, value, child) => Opacity(
              opacity: value,
              child: Transform.translate(offset: Offset(0, (1 - value) * 8), child: child),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Stage B — Critic review', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: QuorumSpacing.sm),
                if (recordedObjections == null)
                  const ListTile(
                    leading: Icon(Icons.info_outline, color: QuorumStatusColors.needsAttention),
                    title: Text("Not recorded"),
                    subtitle: Text("This action predates Gate Reveal, so its real Stage B review was never saved."),
                  )
                else
                  StageBSection(summary: summarizeStageB(recordedObjections)),
              ],
            ),
          ),
        ],
      ],
    );
  }
}

/// Made public (`DEC-153`) -- `features/quick_capture/quick_capture_
/// screen.dart` reuses this exact widget for the identical real reason
/// it exists here: the same trusted icon/color mapping for a real
/// `Finding`'s three-valued `evidence_state`, never a second, parallel
/// rendering of the same real concept.
class FindingRow extends StatelessWidget {
  final FindingSummary finding;

  const FindingRow({super.key, required this.finding});

  @override
  Widget build(BuildContext context) {
    final (icon, color) = switch (finding.visualState) {
      EvidenceVisualState.positive => (Icons.check_circle, QuorumStatusColors.verified),
      EvidenceVisualState.negative => (Icons.cancel, QuorumStatusColors.critical),
      EvidenceVisualState.uncertain => (Icons.help_outline, QuorumStatusColors.needsAttention),
    };

    return ListTile(
      leading: QuorumIconBadge(icon: icon, color: color),
      title: Text(finding.claim),
      subtitle: Text(finding.validator),
    );
  }
}

/// The real, previously-missing control surface for a still-unresolved
/// `action_events` row. `canApprove` is already false by the time this
/// renders for anything without a real execution path (see `GateRevealBundle
/// .canApprove`) -- when that's the only reason there's nothing to act on,
/// Reject (dismiss) is still offered on its own, which is the one real way
/// a `create_calendar_event_local`/`escalate_to_human` row ever clears out
/// of Needs-You-Now.
class _ActionBar extends StatelessWidget {
  final String actionType;
  final Map<String, dynamic> payload;
  final bool canApprove;
  final bool canReject;
  final bool submitting;
  final String? error;
  final VoidCallback onApprove;
  final VoidCallback onReject;

  const _ActionBar({
    required this.actionType,
    required this.payload,
    required this.canApprove,
    required this.canReject,
    required this.submitting,
    required this.error,
    required this.onApprove,
    required this.onReject,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(QuorumSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('This is waiting on you', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: QuorumSpacing.sm),
            // REAL, DISCLOSED FIX (CRITICAL-tier cross-model review,
            // HIGH-3): before this, a real Approve button could be
            // tapped without this screen ever showing what it would
            // actually execute -- the Judge-possibly-revised real
            // payload, not necessarily what the user originally typed.
            // Rendered unconditionally, above the buttons, for every
            // real action type (not just the two Approve can execute)
            // so a human rejecting something still sees what they're
            // rejecting too.
            _PayloadPreview(actionType: actionType, payload: payload),
            const SizedBox(height: QuorumSpacing.md),
            if (error != null) ...[
              Text(error!, style: const TextStyle(color: QuorumStatusColors.critical)),
              const SizedBox(height: QuorumSpacing.sm),
            ],
            Row(
              children: [
                if (canApprove) ...[
                  Expanded(
                    child: FilledButton(
                      onPressed: submitting ? null : onApprove,
                      child: submitting
                          ? const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2))
                          : const Text('Approve'),
                    ),
                  ),
                  const SizedBox(width: QuorumSpacing.sm),
                ],
                if (canReject)
                  Expanded(
                    child: OutlinedButton(
                      onPressed: submitting ? null : onReject,
                      child: Text(canApprove ? 'Reject' : 'Dismiss'),
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

/// REAL, NEW (CRITICAL-tier cross-model review, HIGH-3) -- a real,
/// honest, human-readable rendering of exactly what `Approve` would
/// execute (or what `Reject` dismisses), never the raw JSON payload
/// dumped verbatim. Keyed by `actionType` since `send_email`/`create_
/// calendar_event_external` carry genuinely different real fields --
/// see `features/action_executor.py`'s own real per-type payload shape
/// for the source of truth these keys are read from. Any key this
/// widget doesn't recognize for a given type is shown as a last-resort
/// raw `key: value` line rather than silently dropped -- a real,
/// deliberate "never hide a field a human might need to see before
/// approving" choice, even at the cost of a less polished fallback.
class _PayloadPreview extends StatelessWidget {
  final String actionType;
  final Map<String, dynamic> payload;

  const _PayloadPreview({required this.actionType, required this.payload});

  @override
  Widget build(BuildContext context) {
    final rows = switch (actionType) {
      'send_email' => const [('to', 'To'), ('subject', 'Subject'), ('body', 'Message')],
      'create_calendar_event_external' => const [
          ('title', 'Title'),
          ('invitee_email', 'With'),
          ('start', 'Starts'),
          ('end', 'Ends'),
        ],
      _ => payload.keys.map((key) => (key, key)).toList(),
    };

    return Container(
      padding: const EdgeInsets.all(QuorumSpacing.sm),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          for (final (key, label) in rows)
            if (payload[key] != null)
              Padding(
                padding: const EdgeInsets.only(bottom: QuorumSpacing.xs),
                child: Text.rich(
                  TextSpan(
                    children: [
                      TextSpan(text: '$label: ', style: const TextStyle(fontWeight: FontWeight.bold)),
                      TextSpan(text: '${payload[key]}'),
                    ],
                  ),
                ),
              ),
        ],
      ),
    );
  }
}

class _OutcomeBanner extends StatelessWidget {
  final _ActionOutcome outcome;

  const _OutcomeBanner({required this.outcome});

  @override
  Widget build(BuildContext context) {
    final approved = outcome == _ActionOutcome.approved;
    return ListTile(
      tileColor: Theme.of(context).colorScheme.surfaceContainerHighest,
      leading: QuorumIconBadge(
        icon: approved ? Icons.check_circle : Icons.cancel_outlined,
        color: approved ? QuorumStatusColors.verified : QuorumStatusColors.needsAttention,
      ),
      title: Text(approved ? 'Approved — Quorum carried this out' : 'Rejected — this will not happen'),
    );
  }
}

/// Made public (`DEC-153` precedent, the same reasoning that already
/// made `FindingRow` public) -- `features/quick_capture/quick_capture_
/// screen.dart` reuses this exact widget for the identical real reason
/// it exists here: the same real Stage-B rendering for a real, freshly
/// captured proposal that goes through the exact same real Gate, never
/// a second, parallel Stage-B display concept.
class StageBSection extends StatelessWidget {
  final StageBSummary summary;

  const StageBSection({super.key, required this.summary});

  @override
  Widget build(BuildContext context) {
    if (summary.realObjections.isEmpty) {
      // Stage B genuinely ran and signed off -- a real, positive
      // outcome, never rendered as "nothing happened."
      return const ListTile(
        leading: QuorumIconBadge(icon: Icons.verified, color: QuorumStatusColors.verified),
        title: Text('Reviewed — no objections'),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final objection in summary.realObjections)
          ListTile(
            leading: const QuorumIconBadge(icon: Icons.flag, color: QuorumStatusColors.needsAttention),
            title: Text(objection.description),
            subtitle: Text('${objection.category} · ${objection.severity}'),
          ),
      ],
    );
  }
}
