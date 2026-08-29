// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.
//
// Phase 8 Session 3 (`DEC-157`): every application row gets the same
// neutral `QuorumIconBadge` (no per-status color) -- deliberately, unlike
// Tasks' real per-status color coding. `applications.status` is a
// genuinely open vocabulary (no database `CHECK` constraint,
// `career_pipeline_logic.dart`'s own header confirms only two of the
// four `knownStatusOrder` values are real anywhere in this codebase
// today) -- inventing a color per status now would mean guessing a
// meaning for values that don't exist yet, exactly the kind of
// unrequested architecture `CLAUDE.md` Rule 3 exists to prevent. A
// neutral, identical badge for every row is the honest choice here.

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

  const CareerPipelineScreen({super.key, required this.applications, this.onTapApplication});

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
          _StatusSection(status: status, applications: grouped[status]!, onTap: onTapApplication),
      ],
    );
  }
}

class _StatusSection extends StatelessWidget {
  final String status;
  final List<CareerApplication> applications;
  final void Function(CareerApplication application)? onTap;

  const _StatusSection({required this.status, required this.applications, this.onTap});

  @override
  Widget build(BuildContext context) {
    final badgeColor = Theme.of(context).colorScheme.onSurfaceVariant;

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
                trailing: onTap == null ? null : const Icon(Icons.chevron_right),
                onTap: onTap == null ? null : () => onTap!(applications[i]),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
