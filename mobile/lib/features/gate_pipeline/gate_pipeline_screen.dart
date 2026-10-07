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
import 'package:url_launcher/url_launcher.dart';

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/api/capture_stream_api.dart';
import 'package:quorum_mobile/features/calendar_sync.dart' show CreateLocalEventResult;
import 'package:quorum_mobile/features/gate_pipeline/artifact_links.dart';
import 'package:quorum_mobile/features/gate_pipeline/gate_pipeline_logic.dart';
import 'package:quorum_mobile/features/gate_reveal/gate_reveal_logic.dart';
import 'package:quorum_mobile/features/quick_capture/on_device_correctness.dart';
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

/// Matches `CalendarSync.createLocalEvent()`'s own real signature
/// exactly, re-declared here for the identical reason `ApproveCall`/
/// `RejectCall` are: this screen takes it as a plain injected function
/// rather than importing `calendar_sync.dart` directly.
typedef CreateLocalEventCall = Future<CreateLocalEventResult> Function({
  required String title,
  required DateTime start,
  required DateTime end,
  String? description,
});

/// `DEC-220` (product rebuild Part C, Priority 3) -- matches
/// `on_device_extraction.dart`'s own real `OnDeviceExtractionCall`
/// typedef shape exactly, re-declared here rather than imported for
/// the identical reason `ApproveCall`/`RejectCall`/`CreateLocalEventCall`
/// above already are: this screen stays free of a direct dependency on
/// `package:llamadart`. See `checkOnDeviceExtraction` below for how its
/// result is judged -- genuinely never used to change what this screen
/// submits (it always streams through the real cloud Gate, by design,
/// see this file's own header comment); this is a real, honest,
/// side-channel visibility check only.
typedef OnDeviceExtractAttempt = Future<Map<String, dynamic>> Function(String freeText);

class GatePipelineScreen extends StatefulWidget {
  final CaptureStreamFetcher captureStream;
  final ApproveCall onApprove;
  final RejectCall onReject;

  /// `DEC-191` (product rebuild Block C). Optional, matching every
  /// other injected dependency's own honest-gating convention: when
  /// absent, a real local-calendar-create result renders exactly as
  /// before (an honest "nothing writes a local event from here yet"),
  /// never a crash or a silently-skipped write.
  final CreateLocalEventCall? onCreateLocalEvent;

  /// `DEC-220` (product rebuild Part C, Priority 3) -- the plan's own
  /// named gap: on-device extraction (`quick_capture_router.dart`) was
  /// real and wired for the ordinary, non-streaming capture screen, but
  /// invisible in this one -- the screen Preethish actually opens.
  /// Optional and additive, same honest-gating pattern as every other
  /// injected dependency here: when absent, no on-device row ever
  /// appears, matching this screen's exact prior behavior.
  final OnDeviceExtractAttempt? onDeviceExtract;

  const GatePipelineScreen({
    super.key,
    required this.captureStream,
    required this.onApprove,
    required this.onReject,
    this.onCreateLocalEvent,
    this.onDeviceExtract,
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

  /// `DEC-191`: the real, separate outcome of the on-device calendar
  /// write this screen performs itself -- genuinely distinct from the
  /// backend's own `executed` (which is permanently `False` for
  /// `create_calendar_event_local`, by design, since the real write
  /// never happens server-side). `null` until a local-calendar result
  /// has actually been attempted.
  CreateLocalEventResult? _localEventResult;
  bool _localEventInFlight = false;

  /// `DEC-220` (product rebuild Part C, Priority 3) -- the real, honest
  /// outcome of this screen's own on-device side-channel check. `null`
  /// before a capture starts, or whenever `onDeviceExtract` isn't
  /// configured at all (the honest "not checked" state, never a
  /// fabricated one). Genuinely independent of `_events`/`_view`:
  /// deliberately NOT reduced through `reducePipelineEvents` (which only
  /// ever sees real server-reported stages), kept as its own, separate
  /// client-only fact so the pure reducer's own existing test coverage
  /// stays untouched by this purely additive feature.
  bool _onDeviceChecking = false;
  String? _onDeviceOutcome;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _submit() {
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    final onDeviceExtract = widget.onDeviceExtract;
    setState(() {
      _phase = _Phase.running;
      _events.clear();
      _view = LivePipelineView.empty;
      _approvalInFlight = false;
      _approvalError = null;
      _approvalDone = false;
      _localEventResult = null;
      _localEventInFlight = false;
      _onDeviceChecking = onDeviceExtract != null;
      _onDeviceOutcome = null;
    });

    // Run deliberately CONCURRENTLY with the real cloud stream below,
    // never sequentially before it -- this is a real, local, no-network
    // side check, and this screen's whole point is watching the real
    // cloud Gate resolve as fast as it genuinely does; serializing a
    // multi-second on-device inference in front of that would add real,
    // user-visible delay for a result this screen never acts on anyway.
    if (onDeviceExtract != null) _runOnDeviceCheck(text, onDeviceExtract);

    widget.captureStream(text).listen(
      (event) {
        if (!mounted) return;
        setState(() {
          _events.add(event);
          _view = reducePipelineEvents(_events);
        });
        // Fired exactly once, the moment the real `result` event
        // arrives -- not derived from `_view.isFinished` broadly, so
        // this can never double-fire on a later, unrelated event.
        if (event.name == 'result') _maybeCreateLocalEvent(event.data);
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

  /// `DEC-191`: performs the real on-device write for a genuine
  /// `create_calendar_event_local` result the Gate has approved.
  ///
  /// Checked against the REAL result fields, never inferred from
  /// `executed` -- `executed` is permanently `False` for this action
  /// type (no server-side execution target exists for it, by design),
  /// so using it as the trigger would mean this code never ran at all.
  /// `decision == 'approve'` is the real signal that matters: the Gate
  /// genuinely cleared this proposal, and the on-device write is this
  /// client's own job to finish, honoring the same real privacy
  /// decision that keeps local calendar ground truth off the server
  /// entirely.
  Future<void> _maybeCreateLocalEvent(Map<String, dynamic> result) async {
    final onCreateLocalEvent = widget.onCreateLocalEvent;
    if (onCreateLocalEvent == null) return;
    if (result['domain'] != 'calendar') return;
    if (result['calendar_action'] != 'create_calendar_event_local') return;
    if (result['decision'] != 'approve') return;

    final startRaw = result['event_start'] as String?;
    final endRaw = result['event_end'] as String?;
    final title = result['event_title'] as String?;
    final start = startRaw == null ? null : DateTime.tryParse(startRaw);
    final end = endRaw == null ? null : DateTime.tryParse(endRaw);
    if (start == null || end == null || title == null) {
      // The Gate approved this, but the real fields this client needs
      // to finish the write didn't come through -- an honest failure,
      // never a crash and never a silent no-op.
      if (mounted) {
        setState(() => _localEventResult = const CreateLocalEventResult(
              success: false,
              detail: "The approved event didn't carry enough real detail to write it on-device.",
            ));
      }
      return;
    }

    setState(() => _localEventInFlight = true);
    try {
      final localResult = await onCreateLocalEvent(title: title, start: start, end: end);
      if (mounted) setState(() => _localEventResult = localResult);
    } catch (e) {
      if (mounted) {
        setState(() => _localEventResult = CreateLocalEventResult(success: false, detail: e.toString()));
      }
    } finally {
      if (mounted) setState(() => _localEventInFlight = false);
    }
  }

  /// `DEC-220` (product rebuild Part C, Priority 3) -- runs the real,
  /// on-device extraction attempt and judges it against the same real
  /// correctness bar `quick_capture_router.dart` uses for the ordinary
  /// capture screen, purely for honest visibility here. `check.reason`
  /// is deliberately never shown -- `on_device_correctness.dart`'s own
  /// docstring establishes it as an internal, developer-facing string,
  /// not user-facing copy, and this screen holds that line exactly as
  /// strictly as the router does.
  Future<void> _runOnDeviceCheck(String freeText, OnDeviceExtractAttempt onDeviceExtract) async {
    String outcome;
    try {
      final args = await onDeviceExtract(freeText);
      final check = checkOnDeviceExtraction(args);
      outcome = check.passed
          ? 'Ran on-device (Llama 3.2 3B) -- understood this correctly on its own.'
          : "Tried on-device (Llama 3.2 3B) -- didn't produce a confident reading, so the cloud pipeline below is doing the real work.";
    } catch (e) {
      outcome = "Tried on-device (Llama 3.2 3B) -- couldn't complete, so the cloud pipeline below is doing the real work.";
    }
    if (!mounted) return;
    setState(() {
      _onDeviceChecking = false;
      _onDeviceOutcome = outcome;
    });
  }

  void _reset() {
    setState(() {
      _phase = _Phase.input;
      _controller.clear();
      _events.clear();
      _view = LivePipelineView.empty;
      _onDeviceChecking = false;
      _onDeviceOutcome = null;
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
              if (_onDeviceChecking || _onDeviceOutcome != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: QuorumSpacing.sm),
                  child: _OnDeviceCheckTile(checking: _onDeviceChecking, outcome: _onDeviceOutcome),
                ),
              for (final row in _view.rows) PipelineRowTile(key: ValueKey(row.id), row: row),
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

    // `DEC-191`: a real, tappable link straight into Gmail/Calendar --
    // "it drafted this, here it is" -- whenever this real result
    // carried a real artifact (a genuinely executed CREATE_EMAIL_DRAFT
    // today; any future autonomous Google-API action tomorrow, with no
    // code change needed here). Null, honestly, for every domain/
    // outcome that never produces one -- `artifactLinkFor()` returns
    // null rather than a broken link in that case.
    final link = artifactLinkFor(result['artifact'] as Map<String, dynamic>?);

    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.all(QuorumSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            if (_localEventInFlight || _localEventResult != null) ...[
              _LocalEventStatusRow(inFlight: _localEventInFlight, result: _localEventResult),
              const SizedBox(height: QuorumSpacing.sm),
            ],
            if (link != null) ...[
              OutlinedButton.icon(
                onPressed: () => _openArtifactLink(link),
                icon: const Icon(Icons.open_in_new_rounded, size: 16),
                label: Text(link.label),
              ),
              const SizedBox(height: QuorumSpacing.sm),
            ],
            FilledButton(onPressed: _reset, child: const Text('Done')),
          ],
        ),
      ),
    );
  }

  Future<void> _openArtifactLink(ArtifactLink link) async {
    final uri = Uri.parse(link.url);
    // `launchUrl` returning `false` means no app/browser on the device
    // could handle this real URL -- a real, honest failure mode (never
    // thrown, per `url_launcher`'s own documented contract), surfaced
    // to the user rather than silently swallowed.
    final opened = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (!opened && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Couldn't open ${link.label.toLowerCase()} -- no app available for this link.")),
      );
    }
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

class PipelineRowTile extends StatelessWidget {
  final PipelineRow row;

  const PipelineRowTile({super.key, required this.row});

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

/// `DEC-220` (product rebuild Part C, Priority 3): the real, honest
/// outcome of this screen's own on-device side-channel check -- never
/// styled as pass/fail (`solidPanelDecoration()` with no accent either
/// way), since neither outcome is a Gate finding and neither changes
/// what actually runs below it.
class _OnDeviceCheckTile extends StatelessWidget {
  final bool checking;
  final String? outcome;

  const _OnDeviceCheckTile({required this.checking, required this.outcome});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(QuorumSpacing.sm),
      decoration: solidPanelDecoration(),
      child: Row(
        children: [
          if (checking)
            const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
          else
            const Icon(Icons.memory_rounded, size: 16, color: QuorumDarkGround.textSecondary),
          const SizedBox(width: QuorumSpacing.sm),
          Expanded(
            child: Text(
              checking ? 'Checking on-device (Llama 3.2 3B)...' : outcome!,
              style: QuorumMono.detail(context, color: QuorumDarkGround.textSecondary),
            ),
          ),
        ],
      ),
    );
  }
}

/// `DEC-191`: the real, honest status of this screen's own on-device
/// calendar write -- deliberately separate from every other row above
/// it, since this is the one real outcome the BACKEND never reports at
/// all (it happens entirely on this device).
class _LocalEventStatusRow extends StatelessWidget {
  final bool inFlight;
  final CreateLocalEventResult? result;

  const _LocalEventStatusRow({required this.inFlight, required this.result});

  @override
  Widget build(BuildContext context) {
    if (inFlight) {
      return Container(
        padding: const EdgeInsets.all(QuorumSpacing.sm),
        decoration: solidPanelDecoration(),
        child: const Row(
          children: [
            SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
            SizedBox(width: QuorumSpacing.sm),
            Text('Adding this to your calendar...'),
          ],
        ),
      );
    }
    final outcome = result!;
    final color = outcome.success ? QuorumDarkStatus.verified : QuorumDarkStatus.critical;
    return Container(
      padding: const EdgeInsets.all(QuorumSpacing.sm),
      decoration: solidPanelDecoration(accent: color),
      child: Row(
        children: [
          Icon(outcome.success ? Icons.event_available_rounded : Icons.event_busy_rounded, color: color, size: 20),
          const SizedBox(width: QuorumSpacing.sm),
          Expanded(
            child: Text(
              outcome.success ? 'Added to your on-device calendar.' : outcome.detail,
              style: const TextStyle(color: QuorumDarkGround.textPrimary),
            ),
          ),
        ],
      ),
    );
  }
}
