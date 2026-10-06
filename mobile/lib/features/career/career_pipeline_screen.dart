// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.
//
// REAL, DISCLOSED OVERRIDE (the redesign's own real Career Pipeline
// richness work) -- this header used to say, as a Phase 8 Session 3
// (`DEC-157`) decision, that every application row deliberately gets the
// same neutral badge with no per-status color, reasoned from `applications
// .status` being genuinely open vocabulary. That reasoning is still
// honored in full for a genuinely UNKNOWN status (see `career_pipeline_
// logic.dart`'s own `colorCategoryForStatus()`, whose `default` case
// still falls back to neutral) -- but this session's own approved
// redesign plan explicitly asked for real color-coding on the four real,
// KNOWN statuses specifically, so each row's badge now uses
// `colorCategoryForStatus()`'s real, disclosed mapping instead of a
// single, always-neutral color.
//
// `DEC-212` (product rebuild Part C, visual pass): redesigned onto the
// dark glassmorphic system `calendar_screen.dart`/`tasks_screen.dart`/
// `finance_screen.dart` already carry -- zero logic change
// (`groupByStatus`/`orderedStatusKeys`/`statusLabel`/
// `colorCategoryForStatus` untouched). A REAL, DISCLOSED, MINOR
// SIMPLIFICATION made in the same pass: the dark system's own
// `QuorumDarkStatus` has four colors (verified/needsAttention/
// critical/neutral), one fewer than the legacy `QuorumStatusColors`
// this screen used before (which also had a separate `uncertain`
// blue-grey). `StatusColorCategory.muted` and `.neutral` both now map
// to `QuorumDarkStatus.neutral` -- both were already "quiet,
// non-alarming greys" before this change, just two adjacent shades;
// this loses no real `applications.status` information, only a shade
// distinction between two already-quiet tones.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/career/career_pipeline_logic.dart';
import 'package:quorum_mobile/theme/agent_identity.dart';
import 'package:quorum_mobile/theme/quorum_dark_theme.dart';
import 'package:quorum_mobile/theme/quorum_kit.dart';
import 'package:quorum_mobile/theme/glass.dart';
import 'package:quorum_mobile/theme/spacing.dart';

class CareerPipelineScreen extends StatelessWidget {
  final List<CareerApplication> applications;

  /// Batch 10 Phase 4 -- a real, deferred, injected navigation hook,
  /// same pattern as every other real/external boundary in this
  /// project. Optional and additive: every existing real behavior is
  /// unchanged when this is null (the honest, no-drill-down-configured
  /// state).
  final void Function(CareerApplication application)? onTapApplication;

  /// `DEC-195` (product rebuild Block F remainder) -- the real, first
  /// write control on this screen beyond creating a new application.
  /// Optional and additive, same honest-gating pattern as every other
  /// real write in this app: the per-row "Schedule interview" action
  /// only appears when this is genuinely supplied.
  final void Function(CareerApplication application)? onScheduleInterview;

  const CareerPipelineScreen(
      {super.key,
      required this.applications,
      this.onTapApplication,
      this.onScheduleInterview});

  @override
  Widget build(BuildContext context) {
    final identity = identityOf(QuorumAgent.career);
    final grouped = groupByStatus(applications);
    final orderedKeys = orderedStatusKeys(grouped);

    return QuorumAmbientBackground(
      accent: identity.accent,
      child: SafeArea(
        child: Padding(
          // Same real reason the other redesigned workspaces pad below
          // the toolbar: this screen is PUSHED behind a transparent,
          // `extendBodyBehindAppBar: true` app bar kept only for its
          // real back button.
          padding:
              const EdgeInsets.only(top: kToolbarHeight - QuorumSpacing.md),
          child: orderedKeys.isEmpty
              ? Column(
                  children: [
                    _AgentHeader(identity: identity),
                    const Expanded(
                      child: Center(
                        child: HonestEmptyState(
                          icon: Icons.work_outline_rounded,
                          headline: 'No applications yet',
                          detail: 'Add one with the button below.',
                        ),
                      ),
                    ),
                  ],
                )
              : ListView(
                  padding: const EdgeInsets.fromLTRB(
                      QuorumSpacing.md, 0, QuorumSpacing.md, QuorumSpacing.xxl),
                  children: [
                    _AgentHeader(identity: identity),
                    for (final status in orderedKeys)
                      _StatusSection(
                        status: status,
                        applications: grouped[status]!,
                        accent: identity.accent,
                        onTap: onTapApplication,
                        onScheduleInterview: onScheduleInterview,
                      ),
                  ],
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
          const AgentBadge(agent: QuorumAgent.career, compact: true),
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

class _StatusSection extends StatelessWidget {
  final String status;
  final List<CareerApplication> applications;
  final Color accent;
  final void Function(CareerApplication application)? onTap;
  final void Function(CareerApplication application)? onScheduleInterview;

  const _StatusSection({
    required this.status,
    required this.applications,
    required this.accent,
    this.onTap,
    this.onScheduleInterview,
  });

  @override
  Widget build(BuildContext context) {
    // Every real row in this section shares the same real `status` (that
    // is what groups them into a section at all), so the real color
    // category is computed once per section, not once per row.
    final badgeColor = switch (colorCategoryForStatus(status)) {
      StatusColorCategory.positive => QuorumDarkStatus.verified,
      StatusColorCategory.attention => QuorumDarkStatus.needsAttention,
      StatusColorCategory.muted => QuorumDarkStatus.neutral,
      StatusColorCategory.neutral => QuorumDarkStatus.neutral,
    };

    return Padding(
      padding: const EdgeInsets.only(bottom: QuorumSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SectionHeader(
              label: '${statusLabel(status)} (${applications.length})',
              accent: badgeColor),
          for (var i = 0; i < applications.length; i++) ...[
            if (i > 0) const SizedBox(height: QuorumSpacing.sm),
            _ApplicationRow(
              application: applications[i],
              color: badgeColor,
              onTap: onTap == null ? null : () => onTap!(applications[i]),
              onScheduleInterview: onScheduleInterview == null
                  ? null
                  : () => onScheduleInterview!(applications[i]),
            ),
          ],
        ],
      ),
    );
  }
}

class _ApplicationRow extends StatelessWidget {
  final CareerApplication application;
  final Color color;
  final VoidCallback? onTap;
  final VoidCallback? onScheduleInterview;

  const _ApplicationRow(
      {required this.application,
      required this.color,
      this.onTap,
      this.onScheduleInterview});

  @override
  Widget build(BuildContext context) {
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
                child: Icon(Icons.business_center, size: 18, color: color),
              ),
              const SizedBox(width: QuorumSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(application.company,
                        style: Theme.of(context)
                            .textTheme
                            .titleSmall
                            ?.copyWith(color: QuorumDarkGround.textPrimary)),
                    if (application.role != null) ...[
                      const SizedBox(height: 2),
                      Text(application.role!,
                          style: QuorumMono.detail(context)),
                    ],
                  ],
                ),
              ),
              if (onScheduleInterview != null)
                IconButton(
                  icon: Icon(Icons.event_available_outlined, color: color),
                  tooltip: 'Schedule interview',
                  onPressed: onScheduleInterview,
                ),
              if (onTap != null)
                const Icon(Icons.chevron_right, color: QuorumDarkGround.textTertiary),
            ],
          ),
        ),
      ),
    );
  }
}
