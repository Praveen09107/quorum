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
// KNOWN statuses specifically, so each row's `QuorumIconBadge` now uses
// `colorCategoryForStatus()`'s real, disclosed mapping instead of a
// single, always-neutral color.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/career/career_pipeline_logic.dart';
import 'package:quorum_mobile/theme/quorum_theme.dart';
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

  const CareerPipelineScreen({super.key, required this.applications, this.onTapApplication, this.onScheduleInterview});

  @override
  Widget build(BuildContext context) {
    final grouped = groupByStatus(applications);
    final orderedKeys = orderedStatusKeys(grouped);

    if (orderedKeys.isEmpty) {
      return const Center(child: Text('No applications yet.'));
    }

    return ListView(
      padding: const EdgeInsets.all(QuorumSpacing.md),
      children: [
        for (final status in orderedKeys)
          _StatusSection(
            status: status,
            applications: grouped[status]!,
            onTap: onTapApplication,
            onScheduleInterview: onScheduleInterview,
          ),
      ],
    );
  }
}

class _StatusSection extends StatelessWidget {
  final String status;
  final List<CareerApplication> applications;
  final void Function(CareerApplication application)? onTap;
  final void Function(CareerApplication application)? onScheduleInterview;

  const _StatusSection({required this.status, required this.applications, this.onTap, this.onScheduleInterview});

  @override
  Widget build(BuildContext context) {
    // Every real row in this section shares the same real `status` (that
    // is what groups them into a section at all), so the real color
    // category is computed once per section, not once per row.
    final badgeColor = switch (colorCategoryForStatus(status)) {
      StatusColorCategory.positive => QuorumStatusColors.verified,
      StatusColorCategory.attention => QuorumStatusColors.needsAttention,
      StatusColorCategory.muted => QuorumStatusColors.uncertain,
      StatusColorCategory.neutral => Theme.of(context).colorScheme.onSurfaceVariant,
    };

    return Padding(
      padding: const EdgeInsets.only(bottom: QuorumSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(vertical: QuorumSpacing.sm),
            child: Text(
              '${statusLabel(status)} (${applications.length})',
              style: Theme.of(context).textTheme.titleSmall,
            ),
          ),
          for (var i = 0; i < applications.length; i++) ...[
            if (i > 0) const SizedBox(height: QuorumSpacing.sm),
            Card(
              child: ListTile(
                leading: QuorumIconBadge(icon: Icons.business_center, color: badgeColor),
                title: Text(applications[i].company),
                subtitle: applications[i].role == null ? null : Text(applications[i].role!),
                trailing: onTap == null && onScheduleInterview == null
                    ? null
                    : Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          if (onScheduleInterview != null)
                            IconButton(
                              icon: const Icon(Icons.event_available_outlined),
                              tooltip: 'Schedule interview',
                              onPressed: () => onScheduleInterview!(applications[i]),
                            ),
                          if (onTap != null) const Icon(Icons.chevron_right),
                        ],
                      ),
                onTap: onTap == null ? null : () => onTap!(applications[i]),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
