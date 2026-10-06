// Real widget tests for features/tasks/tasks_screen.dart (`DEC-210`,
// product rebuild Part C visual pass -- the glassmorphic agent-branded
// redesign). Covers the real states this screen has always had: a
// genuinely empty list, a real non-empty list, and the real
// tap-to-complete/cancel bottom sheet -- the redesign changed the
// widget tree, not the underlying contract.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:quorum_mobile/features/tasks/tasks_logic.dart';
import 'package:quorum_mobile/features/tasks/tasks_screen.dart';
import 'package:quorum_mobile/theme/quorum_dark_theme.dart';

TaskData _task(String title, {TaskStatus status = TaskStatus.open, double estimatedHours = 1.0}) {
  return TaskData(taskId: 'task-$title', title: title, estimatedHours: estimatedHours, deadline: null, status: status);
}

Widget _harness(Widget child) => MaterialApp(theme: buildQuorumDarkTheme(), home: child);

void main() {
  testWidgets('a genuinely empty list renders the real agent header and an honest empty state', (tester) async {
    await tester.pumpWidget(_harness(const TasksScreen(tasks: [])));
    await tester.pumpAndSettle();

    expect(find.text('Tasks'), findsOneWidget);
    expect(find.textContaining('No tasks yet'), findsOneWidget);
  });

  testWidgets('a real, non-empty list renders every real task title and status', (tester) async {
    final tasks = [_task('Write the report'), _task('Finished thing', status: TaskStatus.done)];
    await tester.pumpWidget(_harness(TasksScreen(tasks: tasks)));
    await tester.pumpAndSettle();

    expect(find.text('Write the report'), findsOneWidget);
    expect(find.text('Finished thing'), findsOneWidget);
    expect(find.text('Open'), findsOneWidget);
    expect(find.text('Done'), findsOneWidget);
  });

  testWidgets('tapping a real open task with real callbacks shows the real action sheet', (tester) async {
    final tasks = [_task('Write the report')];
    var completed = false;
    await tester.pumpWidget(_harness(TasksScreen(
      tasks: tasks,
      onComplete: (_) async => completed = true,
    )));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Write the report'));
    await tester.pumpAndSettle();

    expect(find.text('Mark as done'), findsOneWidget);
    await tester.tap(find.text('Mark as done'));
    await tester.pumpAndSettle();

    expect(completed, isTrue);
  });

  testWidgets('a real, already-done task is not tappable when no callbacks apply to it', (tester) async {
    final tasks = [_task('Finished thing', status: TaskStatus.done)];
    await tester.pumpWidget(_harness(TasksScreen(
      tasks: tasks,
      onComplete: (_) async {},
      onCancel: (_) async {},
    )));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Finished thing'));
    await tester.pumpAndSettle();

    expect(find.text('Mark as done'), findsNothing);
  });
}
