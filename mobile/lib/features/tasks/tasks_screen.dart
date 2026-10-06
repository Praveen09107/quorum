// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.
//
// `fetchPredictiveRisk` (Phase 6, `DEC-149`) is a real, deliberately
// minimal mobile surface for `features/predictive_risk.py` -- no prior
// spec contract named a screen for this feature at all (see that
// module's own top-of-file docstring for the full account). A small,
// separate banner ABOVE the real task list, not blocking it: a slow or
// failed risk fetch degrades gracefully to simply showing no banner,
// never breaking the one thing this screen already reliably does
// (showing real tasks).
//
// Phase 8 Session 3 (`DEC-157`) real componentry pass: each task row's
// leading icon now signals status by SHAPE (a real, closed
// `TaskStatus` enum -- confirmed safe to switch on exhaustively, unlike
// Career Pipeline's genuinely open `applications.status`), with
// `TaskStatus.done` also getting `QuorumStatusColors.verified` as a
// distinct color -- a real, completed task is a genuinely positive
// outcome worth visually distinguishing, the same way this app's other
// screens never let a positive/neutral/negative signal look identical.
// Open and cancelled share the same neutral tone, distinguished only by
// icon shape -- neither is a "good" or "bad" state on its own.
//
// `DEC-210` (product rebuild Part C, visual pass): redesigned onto the
// dark glassmorphic system `calendar_screen.dart` (`DEC-209`) already
// carried over from `agents_index_screen.dart` -- zero logic change
// (`sortTasks`/`statusLabel`/`formatHours`/`riskMessage` untouched,
// same props, same real tap-to-complete/cancel bottom sheet).

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/predictive_risk/predictive_risk_logic.dart';
import 'package:quorum_mobile/features/tasks/tasks_logic.dart';
import 'package:quorum_mobile/theme/agent_identity.dart';
import 'package:quorum_mobile/theme/glass.dart';
import 'package:quorum_mobile/theme/quorum_dark_theme.dart';
import 'package:quorum_mobile/theme/quorum_kit.dart';
import 'package:quorum_mobile/theme/spacing.dart';

class TasksScreen extends StatelessWidget {
  final List<TaskData> tasks;
  final Future<RiskAssessmentData> Function()? fetchPredictiveRisk;

  /// REAL, DISCLOSED FIX (the redesign's own real bug-fix work): closes
  /// a real, confirmed-live bug -- the trailing status `Chip` below has
  /// looked like a button since this screen was written, but had no
  /// `onPressed`/`onTap` anywhere, and no real backend route existed to
  /// act on a tap even if it had. Both real, independently optional
  /// (the same honest "not yet connected" degrade every other real
  /// fetcher in this app uses): a real open task's row becomes tappable
  /// the moment either is supplied, offering whichever real action(s)
  /// are actually wired.
  final Future<void> Function(String taskId)? onComplete;
  final Future<void> Function(String taskId)? onCancel;

  const TasksScreen(
      {super.key,
      required this.tasks,
      this.fetchPredictiveRisk,
      this.onComplete,
      this.onCancel});

  Future<void> _showActionsFor(BuildContext context, TaskData task) async {
    final messenger = ScaffoldMessenger.of(context);
    await showModalBottomSheet<void>(
      context: context,
      builder: (sheetContext) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Padding(
              padding: const EdgeInsets.all(QuorumSpacing.md),
              child: Text(task.title,
                  style: Theme.of(sheetContext).textTheme.titleMedium),
            ),
            if (onComplete != null)
              ListTile(
                leading: const Icon(Icons.check_circle,
                    color: QuorumDarkStatus.verified),
                title: const Text('Mark as done'),
                onTap: () async {
                  Navigator.of(sheetContext).pop();
                  try {
                    await onComplete!(task.taskId);
                  } catch (e) {
                    messenger.showSnackBar(
                        SnackBar(content: Text("Couldn't mark this done: $e")));
                  }
                },
              ),
            if (onCancel != null)
              ListTile(
                leading: const Icon(Icons.cancel,
                    color: QuorumDarkStatus.needsAttention),
                title: const Text('Cancel task'),
                onTap: () async {
                  Navigator.of(sheetContext).pop();
                  try {
                    await onCancel!(task.taskId);
                  } catch (e) {
                    messenger.showSnackBar(SnackBar(
                        content: Text("Couldn't cancel this task: $e")));
                  }
                },
              ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final identity = identityOf(QuorumAgent.tasks);
    final sorted = sortTasks(tasks);
    final riskFetch = fetchPredictiveRisk;

    return QuorumAmbientBackground(
      accent: identity.accent,
      child: SafeArea(
        child: Padding(
          // Same real reason `calendar_screen.dart` pads below the
          // toolbar: this screen is PUSHED behind a transparent,
          // `extendBodyBehindAppBar: true` app bar kept only for its
          // real back button, since the real "Tasks" identification
          // now lives in this screen's own in-body header.
          padding:
              const EdgeInsets.only(top: kToolbarHeight - QuorumSpacing.md),
          child: sorted.isEmpty
              ? Column(
                  children: [
                    _AgentHeader(identity: identity),
                    if (riskFetch != null)
                      _PredictiveRiskBanner(
                          fetch: riskFetch, accent: identity.accent),
                    const Expanded(
                      child: Center(
                        child: HonestEmptyState(
                          icon: Icons.task_alt_outlined,
                          headline: 'No tasks yet',
                          detail:
                              'Add one with the button below, or capture it in free text.',
                        ),
                      ),
                    ),
                  ],
                )
              : ListView.separated(
                  padding: const EdgeInsets.fromLTRB(
                      QuorumSpacing.md, 0, QuorumSpacing.md, QuorumSpacing.xxl),
                  itemCount: sorted.length + 2,
                  separatorBuilder: (_, index) => index == 0
                      ? const SizedBox.shrink()
                      : const SizedBox(height: QuorumSpacing.sm),
                  itemBuilder: (context, index) {
                    if (index == 0) return _AgentHeader(identity: identity);
                    if (index == 1) {
                      return riskFetch == null
                          ? const SizedBox.shrink()
                          : Padding(
                              padding: const EdgeInsets.only(
                                  bottom: QuorumSpacing.sm),
                              child: _PredictiveRiskBanner(
                                  fetch: riskFetch, accent: identity.accent),
                            );
                    }
                    final task = sorted[index - 2];
                    final (icon, color) = switch (task.status) {
                      TaskStatus.done => (
                          Icons.check_circle,
                          QuorumDarkStatus.verified
                        ),
                      TaskStatus.open => (
                          Icons.radio_button_unchecked,
                          identity.accent
                        ),
                      TaskStatus.cancelled => (
                          Icons.cancel,
                          QuorumDarkGround.textTertiary
                        ),
                    };
                    final canAct = task.status == TaskStatus.open &&
                        (onComplete != null || onCancel != null);
                    return _TaskRow(
                      task: task,
                      icon: icon,
                      color: color,
                      onTap:
                          canAct ? () => _showActionsFor(context, task) : null,
                    );
                  },
                ),
        ),
      ),
    );
  }
}

class _AgentHeader extends StatelessWidget {
  final AgentIdentity identity;

  const _AgentHeader({required this.identity});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding:
          const EdgeInsets.fromLTRB(0, QuorumSpacing.md, 0, QuorumSpacing.sm),
      child: Row(
        children: [
          const AgentBadge(agent: QuorumAgent.tasks, compact: true),
          const SizedBox(width: QuorumSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(identity.name,
                    style: Theme.of(context)
                        .textTheme
                        .headlineSmall
                        ?.copyWith(color: QuorumDarkGround.textPrimary)),
                Text(identity.purpose,
                    style: Theme.of(context)
                        .textTheme
                        .bodySmall
                        ?.copyWith(color: QuorumDarkGround.textSecondary)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TaskRow extends StatelessWidget {
  final TaskData task;
  final IconData icon;
  final Color color;
  final VoidCallback? onTap;

  const _TaskRow(
      {required this.task,
      required this.icon,
      required this.color,
      this.onTap});

  @override
  Widget build(BuildContext context) {
    // `Material` is required here, not decorative -- `InkWell` needs a
    // `Material` ancestor to render its ink response at all, and a
    // bare `Container` doesn't provide one (confirmed live by this
    // row's own widget test: "No Material widget found" before this
    // fix). Transparent so it never paints over the real decoration
    // below, the same real pattern `glass.dart::GlassPanel` already
    // establishes for its own `onTap`.
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(QuorumRadius.md),
        child: Container(
          padding: const EdgeInsets.all(QuorumSpacing.md),
          decoration: solidPanelDecoration(accent: color),
          child: Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.14),
                  shape: BoxShape.circle,
                  border: Border.all(color: color.withValues(alpha: 0.4)),
                ),
                child: Icon(icon, size: 18, color: color),
              ),
              const SizedBox(width: QuorumSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(task.title,
                        style: Theme.of(context)
                            .textTheme
                            .titleSmall
                            ?.copyWith(color: QuorumDarkGround.textPrimary)),
                    const SizedBox(height: 2),
                    Text(
                      task.deadline == null
                          ? formatHours(task.estimatedHours)
                          : '${formatHours(task.estimatedHours)} · due ${task.deadline!.toIso8601String().split('T').first}',
                      style: QuorumMono.detail(context),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: QuorumSpacing.sm),
              StatusPill(
                  label: statusLabel(task.status), icon: icon, color: color),
            ],
          ),
        ),
      ),
    );
  }
}

/// A real, deliberately quiet loading/error state: this banner is a
/// bonus on top of the real task list, never something worth spinning
/// or erroring loudly over. Loading and error states both render as
/// nothing at all -- only a real, successfully-fetched assessment ever
/// shows a real message.
class _PredictiveRiskBanner extends StatelessWidget {
  final Future<RiskAssessmentData> Function() fetch;
  final Color accent;

  const _PredictiveRiskBanner({required this.fetch, required this.accent});

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<RiskAssessmentData>(
      future: fetch(),
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done ||
            snapshot.hasError ||
            !snapshot.hasData) {
          return const SizedBox.shrink();
        }
        final risk = snapshot.data!;
        // Three real, distinct states -- see file header for why this
        // now matches the "never collapse a genuine ambiguity into a
        // pass or fail" discipline this project already applies
        // elsewhere.
        //
        // Color choice corrected by review (`DEC-157` review finding):
        // `critical`, not `uncertain`, is the real, established color for
        // a negative/failure outcome -- confirmed directly against this
        // codebase's own two other real precedents,
        // `gate_reveal_screen.dart`'s `EvidenceVisualState.negative` and
        // `negotiation_screen.dart`'s `MetricVisualDirection.worsens`,
        // both of which already map to `critical`. `uncertain` is
        // reserved for a genuinely NEUTRAL, unchanged state (that same
        // file's own `MetricVisualDirection.unchanged`) -- a real
        // predicted busy week (this banner's own most actionable state,
        // carrying a real, quantified historical adjustment rate) is not
        // that; using `uncertain` for it would have made this banner's
        // single most important signal read as LESS alarming than "we
        // don't know," backwards from what a predictive-risk warning
        // should communicate.
        final (IconData icon, Color color) = risk.matchingHistoricalWeeks == 0
            ? (Icons.help_outline, QuorumDarkStatus.needsAttention)
            : risk.isAtRisk
                ? (Icons.warning_amber_rounded, QuorumDarkStatus.critical)
                : (Icons.check_circle_outline, QuorumDarkStatus.verified);
        return GlassPanel(
          accent: color,
          accentStrength: risk.matchingHistoricalWeeks == 0 ? 0.4 : 1.0,
          child: Row(
            children: [
              Icon(icon, size: 18, color: color),
              const SizedBox(width: QuorumSpacing.sm),
              Expanded(
                child: Text(riskMessage(risk),
                    style: Theme.of(context)
                        .textTheme
                        .bodyMedium
                        ?.copyWith(color: QuorumDarkGround.textPrimary)),
              ),
            ],
          ),
        );
      },
    );
  }
}
