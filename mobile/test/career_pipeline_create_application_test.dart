// Real widget tests for the new "+ New application" flow (`DEC-194`,
// product rebuild Block F) -- the first real write path the Career
// pipeline screen has ever had. Exercises the real nav chain: YouScreen
// -> Career pipeline preview card -> CareerPipelineScreen -> FAB ->
// the new application sheet -> submit -> real list refresh.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:quorum_mobile/api/create_application_api.dart';
import 'package:quorum_mobile/features/career/career_pipeline_logic.dart';
import 'package:quorum_mobile/features/you/you_logic.dart';
import 'package:quorum_mobile/features/you/you_screen.dart';

Future<DeletionResultData> _unconfiguredDeletion() => throw UnimplementedError();

void main() {
  testWidgets('submitting the new-application form refreshes the real list and shows a success snackbar', (tester) async {
    var fetchCallCount = 0;
    var createCallCount = 0;
    String? capturedCompany;
    String? capturedRole;

    final screen = YouScreen(
      onConfirmDelete: _unconfiguredDeletion,
      fetchCareerApplications: () async {
        fetchCallCount++;
        if (fetchCallCount == 1) {
          return const [CareerApplication(applicationId: 'a1', company: 'Notion', status: 'applied')];
        }
        return const [
          CareerApplication(applicationId: 'a1', company: 'Notion', status: 'applied'),
          CareerApplication(applicationId: 'a2', company: 'Stripe', status: 'applied'),
        ];
      },
      createApplication: ({required String company, String? role, DateTime? deadline}) async {
        createCallCount++;
        capturedCompany = company;
        capturedRole = role;
        return const CreateApplicationResult(executed: true, decision: 'approve', company: 'Stripe');
      },
    );

    await tester.pumpWidget(MaterialApp(home: Scaffold(body: screen)));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Career pipeline'));
    await tester.pumpAndSettle();

    expect(find.text('Notion'), findsOneWidget);

    await tester.tap(find.byIcon(Icons.add));
    await tester.pumpAndSettle();

    await tester.enterText(find.widgetWithText(TextField, 'Company'), 'Stripe');
    await tester.enterText(find.widgetWithText(TextField, 'Role (optional)'), 'Backend Engineer');
    await tester.tap(find.text('Add application'));
    await tester.pumpAndSettle();

    expect(createCallCount, 1);
    expect(capturedCompany, 'Stripe');
    expect(capturedRole, 'Backend Engineer');
    expect(fetchCallCount, 2); // one initial load, one real refresh after create
    expect(find.text('Stripe'), findsOneWidget);
    expect(find.textContaining('Added Stripe'), findsOneWidget);
  });

  testWidgets('a real Gate rejection shows an honest decline message, not a fabricated success', (tester) async {
    final screen = YouScreen(
      onConfirmDelete: _unconfiguredDeletion,
      fetchCareerApplications: () async => const [],
      createApplication: ({required String company, String? role, DateTime? deadline}) async {
        return const CreateApplicationResult(executed: false, decision: 'reject', company: null);
      },
    );

    await tester.pumpWidget(MaterialApp(home: Scaffold(body: screen)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Career pipeline'));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.add));
    await tester.pumpAndSettle();
    await tester.enterText(find.widgetWithText(TextField, 'Company'), 'Stripe');
    await tester.tap(find.text('Add application'));
    await tester.pumpAndSettle();

    expect(find.textContaining('Gate declined'), findsOneWidget);
  });

  testWidgets('no FAB appears when createApplication is not configured, matching the honest-gating precedent', (tester) async {
    final screen = YouScreen(
      onConfirmDelete: _unconfiguredDeletion,
      fetchCareerApplications: () async => const [CareerApplication(applicationId: 'a1', company: 'Notion', status: 'applied')],
    );

    await tester.pumpWidget(MaterialApp(home: Scaffold(body: screen)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Career pipeline'));
    await tester.pumpAndSettle();

    expect(find.byType(FloatingActionButton), findsNothing);
  });
}
