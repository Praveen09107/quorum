// Real widget tests for the new "Schedule interview" flow (`DEC-195`,
// product rebuild Block F remainder) -- the Career pipeline's second
// real write control.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:quorum_mobile/api/schedule_interview_api.dart';
import 'package:quorum_mobile/features/career/career_pipeline_logic.dart';
import 'package:quorum_mobile/features/you/you_logic.dart';
import 'package:quorum_mobile/features/you/you_screen.dart';

Future<DeletionResultData> _unconfiguredDeletion() => throw UnimplementedError();

void main() {
  testWidgets('scheduling an interview refreshes the real list and shows a success snackbar', (tester) async {
    var scheduleCallCount = 0;
    String? capturedApplicationId;
    String? capturedFormat;

    final screen = YouScreen(
      onConfirmDelete: _unconfiguredDeletion,
      fetchCareerApplications: () async => const [CareerApplication(applicationId: 'a1', company: 'Notion', status: 'applied')],
      scheduleInterview: ({required String applicationId, DateTime? scheduledAt, String? format}) async {
        scheduleCallCount++;
        capturedApplicationId = applicationId;
        capturedFormat = format;
        return const ScheduleInterviewResult(executed: true, decision: 'approve');
      },
    );

    await tester.pumpWidget(MaterialApp(home: Scaffold(body: screen)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Career pipeline'));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.event_available_outlined));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Video'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Schedule'));
    await tester.pumpAndSettle();

    expect(scheduleCallCount, 1);
    expect(capturedApplicationId, 'a1');
    expect(capturedFormat, 'video');
    expect(find.textContaining('Interview scheduled with Notion'), findsOneWidget);
  });

  testWidgets('a real Gate rejection shows an honest decline message, not a fabricated success', (tester) async {
    final screen = YouScreen(
      onConfirmDelete: _unconfiguredDeletion,
      fetchCareerApplications: () async => const [CareerApplication(applicationId: 'a1', company: 'Notion', status: 'applied')],
      scheduleInterview: ({required String applicationId, DateTime? scheduledAt, String? format}) async {
        return const ScheduleInterviewResult(executed: false, decision: 'reject');
      },
    );

    await tester.pumpWidget(MaterialApp(home: Scaffold(body: screen)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Career pipeline'));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.event_available_outlined));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Schedule'));
    await tester.pumpAndSettle();

    expect(find.textContaining('Gate declined to schedule'), findsOneWidget);
  });

  testWidgets('no schedule-interview icon appears when not configured, matching the honest-gating precedent', (tester) async {
    final screen = YouScreen(
      onConfirmDelete: _unconfiguredDeletion,
      fetchCareerApplications: () async => const [CareerApplication(applicationId: 'a1', company: 'Notion', status: 'applied')],
    );

    await tester.pumpWidget(MaterialApp(home: Scaffold(body: screen)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Career pipeline'));
    await tester.pumpAndSettle();

    expect(find.byIcon(Icons.event_available_outlined), findsNothing);
  });
}
