// Real widget tests for the new "Update status" flow (`DEC-218`,
// product rebuild Part C, Priority 2 completion) -- the Career
// pipeline's third real write control, closing the plan's own named
// gap: a status could only ever be changed via free-text capture
// before this.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:quorum_mobile/api/update_application_status_api.dart';
import 'package:quorum_mobile/features/career/career_pipeline_logic.dart';
import 'package:quorum_mobile/features/you/you_logic.dart';
import 'package:quorum_mobile/features/you/you_screen.dart';

Future<DeletionResultData> _unconfiguredDeletion() => throw UnimplementedError();

void main() {
  testWidgets('updating a status refreshes the real list and shows a success snackbar', (tester) async {
    var updateCallCount = 0;
    String? capturedApplicationId;
    String? capturedNewStatus;

    final screen = YouScreen(
      onConfirmDelete: _unconfiguredDeletion,
      fetchCareerApplications: () async => const [CareerApplication(applicationId: 'a1', company: 'Notion', status: 'applied')],
      updateApplicationStatus: ({required String applicationId, required String newStatus}) async {
        updateCallCount++;
        capturedApplicationId = applicationId;
        capturedNewStatus = newStatus;
        return UpdateApplicationStatusResult(executed: true, decision: 'approve', stakes: 'S2', company: 'Notion', newStatus: newStatus);
      },
    );

    await tester.pumpWidget(MaterialApp(home: Scaffold(body: screen)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Career pipeline'));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.flag_outlined));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Offer'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Update status'));
    await tester.pumpAndSettle();
    // `DEC-214`: the real Gate verdict sheet now opens before the
    // SnackBar -- dismiss it to reach the real post-submit state.
    await tester.tap(find.text('Done'));
    await tester.pumpAndSettle();

    expect(updateCallCount, 1);
    expect(capturedApplicationId, 'a1');
    expect(capturedNewStatus, 'offer');
    expect(find.textContaining('Notion moved to Offer'), findsOneWidget);
  });

  testWidgets('a real Gate rejection shows an honest decline message, not a fabricated success', (tester) async {
    final screen = YouScreen(
      onConfirmDelete: _unconfiguredDeletion,
      fetchCareerApplications: () async => const [CareerApplication(applicationId: 'a1', company: 'Notion', status: 'applied')],
      updateApplicationStatus: ({required String applicationId, required String newStatus}) async {
        return const UpdateApplicationStatusResult(executed: false, decision: 'reject', stakes: 'S2');
      },
    );

    await tester.pumpWidget(MaterialApp(home: Scaffold(body: screen)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Career pipeline'));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.flag_outlined));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Offer'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Update status'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Done'));
    await tester.pumpAndSettle();

    expect(find.textContaining('Gate declined that status change'), findsOneWidget);
  });

  testWidgets('no update-status icon appears when not configured, matching the honest-gating precedent', (tester) async {
    final screen = YouScreen(
      onConfirmDelete: _unconfiguredDeletion,
      fetchCareerApplications: () async => const [CareerApplication(applicationId: 'a1', company: 'Notion', status: 'applied')],
    );

    await tester.pumpWidget(MaterialApp(home: Scaffold(body: screen)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Career pipeline'));
    await tester.pumpAndSettle();

    expect(find.byIcon(Icons.flag_outlined), findsNothing);
  });
}
