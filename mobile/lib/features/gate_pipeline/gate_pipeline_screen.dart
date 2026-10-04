// The live Gate pipeline screen (`DEC-189` Block B) -- the centerpiece
// of this product rebuild.
//
// `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §12.1 names the interaction
// this product should own: "a verification check resolving is a real,
// literal, satisfying interaction, not a metaphor buried in copy."
// Every screen built before this one rendered a finished verdict --
// this is the first screen that shows the Gate actually working, stage
// by stage, as `POST /capture/stream` reports it happening for real.
//
// Deliberately NOT wired through the on-device-first
// `quick_capture_router.dart`: watching the pipeline resolve live is a
// cloud-first interaction by its own nature (the whole point is seeing
// the real Stage A/B calls happen), so this screen always submits
// straight to the streaming endpoint. The on-device/cloud routing
// question is orthogonal to this screen and stays exactly as it is for
// the ordinary, non-streaming `QuickCaptureScreen`.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/api/capture_stream_api.dart';
import 'package:quorum_mobile/features/gate_pipeline/gate_pipeline_logic.dart';
import 'package:quorum_mobile/features/gate_reveal/gate_reveal_logic.dart';
import 'package:quorum_mobile/theme/agent_identity.dart';
import 'package:quorum_mobile/theme/glass.dart';
import 'package:quorum_mobile/theme/quorum_dark_theme.dart';
import 'package:quorum_mobile/theme/quorum_kit.dart';
import 'package:quorum_mobile/theme/spacing.dart';

/// Backend-agnostic signatures this screen depends on for the S3
/// approve/reject terminal bar -- matches `action_approval_api.dart`'s
/// own real types exactly, re-declared here rather than imported so
/// this screen never needs to import an API client directly (matching
/// `quick_capture_screen.dart`'s own existing injected-function
/// convention).
typedef ApproveCall = Future<void> Function(String proposalId);
typedef RejectCall = Future<void> Function(String proposalId);

class GatePipelineScreen extends StatefulWidget {
  final CaptureStreamFetcher captureStream;
  final ApproveCall onApprove;
  final RejectCall onReject;

  const GatePipelineScreen({
    super.key,
    required this.captureStream,
    required this.onApprove,
    required this.onReject,
  });

  @override
  State<GatePipelineScreen> createState() => _GatePipelineScreenState();
}

enum _Phase { input, running }

class _GatePipelineScreenState extends State<GatePipelineScreen> {
  final _controller = TextEditingController();
  _Phase _phase = _Phase.input;

  final List<GateEvent> _events = [];
  LivePipelineView _view = LivePipelineView.empty;

  /// Set once approve/reject has actually been tapped, so the terminal
  /// bar can show its own real in-flight/error state without a second
  /// StatefulWidget.
  bool _approvalInFlight = false;
  String? _approvalError;
  bool _approvalDone = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _submit() {
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    setState(() {
      _phase = _Phase.running;
      _events.clear();
      _view = LivePipelineView.empty;
      _approvalInFlight = false;
      _approvalError = null;
      _approvalDone = false;
    });

    widget.captureStream(text).listen(
      (event) {
        if (!mounted) return;
        setState(() {
          _events.add(event);
          _view = reducePipelineEvents(_events);
        });
      },
      onError: (Object error) {
        if (!mounted) return;
        final message = error is ApiException ? error.message : 'Something went wrong watching that happen.';
        setState(() {
          _events.add(GateEvent(name: 'error', data: {'event': 'error', 'detail': message}));
          _view = reducePipelineEvents(_events);
        });
      },
    );
  }

  void _reset() {
    setState(() {
      _phase = _Phase.input;
      _controller.clear();
      _events.clear();
      _view = LivePipelineView.empty;
    });
  }

  Future<void> _approve(String proposalId) async {
    setState(() {
      _approvalInFlight = true;
      _approvalError = null;
    });
    try {
      await widget.onApprove(proposalId);
      if (mounted) setState(() => _approvalDone = true);
    } catch (e) {
      if (mounted) setState(() => _approvalError = e is ApiException ? e.message : 'Could not approve that.');
    } finally {
      if (mounted) setState(() => _approvalInFlight = false);
    }
  }

  Future<void> _reject(String proposalId) async {
    setState(() {
      _approvalInFlight = true;
      _approvalError = null;
    });
    try {
      await widget.onReject(proposalId);
      if (mounted) setState(() => _approvalDone = true);
    } catch (e) {
      if (mounted) setState(() => _approvalError = e is ApiException ? e.message : 'Could not reject that.');
    } finally {
      if (mounted) setState(() => _approvalInFlight = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: QuorumDarkGround.base,
      appBar: AppBar(
        title: const Text('Capture'),
        actions: [
          if (_phase == _Phase.running && _view.isFinished)
            IconButton(onPressed: _reset, icon: const Icon(Icons.add_rounded), tooltip: 'New capture'),
        ],
      ),
      body: QuorumAmbientBackground(
        accent: _ambientAccent(),
        child: SafeArea(
          child: _phase == _Phase.input ? _buildInput(context) : _buildPipeline(context),
        ),
      ),
    );
  }

  /// The acting agent's accent, once routing has reported a real
  /// `action_type` -- tints the ambient background so the screen reads
  /// as belonging to whichever agent is actually at work. Null (the
  /// default neutral tint) before routing, or for an action type this
  /// screen doesn't map to a known domain -- honest rather than a
  /// guessed color.
  Color? _ambientAccent() {
    final actionType = _view.actionType;
    if (actionType == null) return null;
    final agent = agentForDomain(_domainFor(actionType));
    return agent == null ? null : identityOf(agent).accent;
  }

  Widget _buildInput(BuildContext context) {
    const examples = [
      'draft a reply to Sarah about the proposal',
      'log ₹450 for lunch',
      'block 2 hours Thursday for deep work',
      'remind me to follow up with the recruiter',
    ];
    return Padding(
      padding: const EdgeInsets.all(QuorumSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            'What should Quorum do?',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(color: QuorumDarkGround.textPrimary),
          ),
          const SizedBox(height: QuorumSpacing.xs),
          Text(
            'Every real check the Gate runs, live, as it runs it.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: QuorumDarkGround.textSecondary),
          ),
          const SizedBox(height: QuorumSpacing.lg),
          GlassPanel(
            accent: const Color(0xFF22D3EE),
            child: TextField(
              controller: _controller,
              minLines: 2,
              maxLines: 5,
              autofocus: true,
              style: const TextStyle(color: QuorumDarkGround.textPrimary),
              cursorColor: const Color(0xFF22D3EE),
              decoration: const InputDecoration(
                border: InputBorder.none,
                hintText: 'Type what you want to get done...',
                hintStyle: TextStyle(color: QuorumDarkGround.textTertiary),
              ),
              textInputAction: TextInputAction.done,
              onSubmitted: (_) => _submit(),
            ),
          ),
          const SizedBox(height: QuorumSpacing.md),
          Wrap(
            spacing: QuorumSpacing.sm,
            runSpacing: QuorumSpacing.sm,
            children: [
              for (final example in examples)
                ActionChip(
                  label: Text(example),
                  onPressed: () => setState(() => _controller.text = example),
                ),
            ],
          ),
          const SizedBox(height: QuorumSpacing.lg),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: _submit,
              icon: const Icon(Icons.bolt_rounded),
              label: const Text('Run it through the Gate'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPipeline(BuildContext context) {
    return Column(
      children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.all(QuorumSpacing.md),
            children: [
              for (final row in _view.rows) _PipelineRowTile(key: ValueKey(row.id), row: row),
              if (_view.error != null) _ErrorCard(error: _view.error!),
            ],
          ),
        ),
        if (_view.isFinished) _buildTerminalBar(context),
      ],
    );
  }

  Widget _buildTerminalBar(BuildContext context) {
    final result = _view.result;
    if (result == null) {
      // A terminal error with no real result -- nothing to approve,
      // just a way back to try again.
      return SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.all(QuorumSpacing.md),
          child: SizedBox(
            width: double.infinity,
            child: OutlinedButton(onPressed: _reset, child: const Text('Try again')),
          ),
        ),
      );
    }

    final decision = result['decision'] as String?;
    final stakes = result['stakes'] as String?;
    final executed = result['executed'] == true;

    // S3 requires explicit human approval in every mode, no exception --
    // the single hardest rule in this architecture (CLAUDE.md). This
    // screen enforces it the only way a UI can: it shows Approve/Reject
    // buttons ONLY for a genuine, unresolved S3 decision, and never
    // auto-dismisses or auto-executes one. `executed == false` is the
    // ORDINARY case for a real S3 proposal, not a rare one -- it means
    // the Gate cleared it and is waiting on the human.
    final needsHumanApproval = stakes == 'S3' && decision == 'approve' && !executed && !_approvalDone;

    if (needsHumanApproval) {
      // `trace_id` on the real `done` event IS the real proposal id --
      // `gate/orchestration.py` sets it to `str(proposal.proposal_id)`
      // on every verdict, confirmed directly rather than assumed.
      final doneEvent = _events.lastWhere((e) => e.name == 'done', orElse: () => const GateEvent(name: '', data: {}));
      final traceId = doneEvent.data['trace_id'] as String?;
      if (traceId == null) {
        // Genuinely should not happen for a real S3 approve verdict --
        // rendered honestly rather than silently disabling the buttons.
        return const SafeArea(
          top: false,
          child: Padding(
            padding: EdgeInsets.all(QuorumSpacing.md),
            child: Text(
              "Couldn't find this action's id -- try reopening it from Activity.",
              style: TextStyle(color: QuorumDarkStatus.critical),
            ),
          ),
        );
      }

      return SafeArea(
        top: false,
        child: Container(
          padding: const EdgeInsets.all(QuorumSpacing.md),
          decoration: const BoxDecoration(
            color: QuorumDarkGround.surface,
            border: Border(top: BorderSide(color: QuorumDarkGround.hairline)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              // Never approve blind -- the full payload is shown above
              // the buttons, the same real safety property
              // `gate_reveal_screen.dart` already established.
              if (result['email_recipient'] != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: QuorumSpacing.sm),
                  child: Text(
                    'To: ${result['email_recipient']}',
                    style: QuorumMono.detail(context, color: QuorumDarkGround.textSecondary),
                  ),
                ),
              if (_approvalError != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: QuorumSpacing.sm),
                  child: Text(_approvalError!, style: const TextStyle(color: QuorumDarkStatus.critical)),
                ),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: _approvalInFlight ? null : () => _reject(traceId),
                      child: const Text('Reject'),
                    ),
                  ),
                  const SizedBox(width: QuorumSpacing.sm),
                  Expanded(
                    child: FilledButton(
                      onPressed: _approvalInFlight ? null : () => _approve(traceId),
                      child: _approvalInFlight
                          ? const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2))
                          : const Text('Approve'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      );
    }

    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.all(QuorumSpacing.md),
        child: SizedBox(
          width: double.infinity,
          child: FilledButton(onPressed: _reset, child: const Text('Done')),
        ),
      ),
    );
  }

  String _domainFor(String actionType) {
    // `action_type` values are the real backend enum
    // (`send_email`/`create_task`/...), while agent identity is keyed
    // by domain (`email`/`tasks`/...) -- the prefix before the first
    // underscore is not reliable for every type, so this only covers
    // the common cases used for the ambient accent; an unmatched type
    // falls through to no accent, which is honest rather than wrong.
    if (actionType.contains('email')) return 'email';
    if (actionType.contains('calendar')) return 'calendar';
    if (actionType.contains('task')) return 'tasks';
    if (actionType.contains('expense') || actionType.contains('budget')) return 'finance';
    if (actionType.contains('application') || actionType.contains('career')) return 'career';
    return '';
  }
}

class _PipelineRowTile extends StatelessWidget {
  final PipelineRow row;

  const _PipelineRowTile({super.key, required this.row});

  @override
  Widget build(BuildContext context) {
    final appearance = row.isPending ? null : _appearanceFor(row.status);
    return Padding(
      padding: const EdgeInsets.only(bottom: QuorumSpacing.sm),
      child: AnimatedSwitcher(
        duration: (MediaQuery.maybeDisableAnimationsOf(context) ?? false)
            ? Duration.zero
            : const Duration(milliseconds: 220),
        child: Container(
          key: ValueKey('${row.id}-${row.status}'),
          decoration: solidPanelDecoration(accent: appearance?.color),
          padding: const EdgeInsets.all(QuorumSpacing.sm),
          child: EvidenceRow(
            validatorName: row.label,
            claim: row.detail ?? '',
            state: row.isPending ? null : _visualStateFor(row.status),
            elapsedMs: row.durationMs,
            pending: row.isPending,
          ),
        ),
      ),
    );
  }

  ({Color color, IconData icon, String label})? _appearanceFor(PipelineRowStatus status) {
    switch (status) {
      case PipelineRowStatus.verified:
        return evidenceAppearance(EvidenceVisualState.positive);
      case PipelineRowStatus.contradicted:
        return evidenceAppearance(EvidenceVisualState.negative);
      case PipelineRowStatus.noData:
        return evidenceAppearance(EvidenceVisualState.uncertain);
      case PipelineRowStatus.neutral:
      case PipelineRowStatus.failed:
      case PipelineRowStatus.pending:
        return null;
    }
  }

  EvidenceVisualState _visualStateFor(PipelineRowStatus status) {
    switch (status) {
      case PipelineRowStatus.verified:
        return EvidenceVisualState.positive;
      case PipelineRowStatus.contradicted:
      case PipelineRowStatus.failed:
        return EvidenceVisualState.negative;
      case PipelineRowStatus.noData:
      case PipelineRowStatus.neutral:
      case PipelineRowStatus.pending:
        return EvidenceVisualState.uncertain;
    }
  }
}

class _ErrorCard extends StatelessWidget {
  final PipelineError error;

  const _ErrorCard({required this.error});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(top: QuorumSpacing.sm),
      padding: const EdgeInsets.all(QuorumSpacing.md),
      decoration: solidPanelDecoration(accent: QuorumDarkStatus.critical),
      child: Row(
        children: [
          const Icon(Icons.error_outline_rounded, color: QuorumDarkStatus.critical, size: 20),
          const SizedBox(width: QuorumSpacing.sm),
          Expanded(child: Text(error.detail, style: const TextStyle(color: QuorumDarkGround.textPrimary))),
        ],
      ),
    );
  }
}
