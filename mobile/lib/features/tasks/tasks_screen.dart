// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/tasks/tasks_logic.dart';

class TasksScreen extends StatelessWidget {
  final List<TaskData> tasks;

  const TasksScreen({super.key, required this.tasks});

  @override
  Widget build(BuildContext context) {
    final sorted = sortTasks(tasks);

    if (sorted.isEmpty) {
      return const Center(child: Text('No tasks yet.'));
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: sorted.length,
      itemBuilder: (context, index) {
        final task = sorted[index];
        return Card(
          child: ListTile(
            title: Text(task.title),
            subtitle: Text(
              task.deadline == null
                  ? formatHours(task.estimatedHours)
                  : '${formatHours(task.estimatedHours)} · due ${task.deadline!.toIso8601String().split('T').first}',
            ),
            trailing: Chip(label: Text(statusLabel(task.status))),
          ),
        );
      },
    );
  }
}
