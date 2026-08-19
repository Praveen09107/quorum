// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/career/career_pipeline_logic.dart';

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
      padding: const EdgeInsets.all(16),
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
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: Text(
            '${statusLabel(status)} (${applications.length})',
            style: Theme.of(context).textTheme.titleSmall,
          ),
        ),
        for (final application in applications)
          Card(
            child: ListTile(
              title: Text(application.company),
              subtitle: application.role == null ? null : Text(application.role!),
              trailing: onTap == null ? null : const Icon(Icons.chevron_right),
              onTap: onTap == null ? null : () => onTap!(application),
            ),
          ),
      ],
    );
  }
}
