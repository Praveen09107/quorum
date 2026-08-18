// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/career/career_pipeline_logic.dart';

class CareerPipelineScreen extends StatelessWidget {
  final List<CareerApplication> applications;

  const CareerPipelineScreen({super.key, required this.applications});

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
        for (final status in orderedKeys) _StatusSection(status: status, applications: grouped[status]!),
      ],
    );
  }
}

class _StatusSection extends StatelessWidget {
  final String status;
  final List<CareerApplication> applications;

  const _StatusSection({required this.status, required this.applications});

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
            ),
          ),
      ],
    );
  }
}
