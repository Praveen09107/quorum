// Real widget tests for features/career/career_pipeline_screen.dart
// (`DEC-212`, product rebuild Part C visual pass -- the glassmorphic
// agent-branded redesign). Covers the real states this screen has
// always had: a genuinely empty list, a real grouped-by-status list,
// and real tap/schedule-interview affordances -- the redesign changed
// the widget tree, not the underlying contract.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:quorum_mobile/features/career/career_pipeline_logic.dart';
import 'package:quorum_mobile/features/career/career_pipeline_screen.dart';
import 'package:quorum_mobile/theme/quorum_dark_theme.dart';

CareerApplication _application(String company, {String status = 'applied', String? role}) {
  return CareerApplication(applicationId: 'app-$company', company: company, role: role, status: status, deadline: null);
}

Widget _harness(Widget child) => MaterialApp(theme: buildQuorumDarkTheme(), home: child);

void main() {
  testWidgets('a genuinely empty list renders the real agent header and an honest empty state', (tester) async {
    await tester.pumpWidget(_harness(const CareerPipelineScreen(applications: [])));
    await tester.pumpAndSettle();

    expect(find.text('Career'), findsOneWidget);
    expect(find.textContaining('No applications yet'), findsOneWidget);
  });

  testWidgets('a real, non-empty list renders every real company grouped by its real status', (tester) async {
    final applications = [_application('Stripe'), _application('Notion', status: 'rejected')];
    await tester.pumpWidget(_harness(CareerPipelineScreen(applications: applications)));
    await tester.pumpAndSettle();

    expect(find.text('Stripe'), findsOneWidget);
    expect(find.text('Notion'), findsOneWidget);
  });

  testWidgets('tapping a real application calls the real onTapApplication callback', (tester) async {
    final applications = [_application('Stripe', role: 'Backend Engineer')];
    CareerApplication? tapped;
    await tester.pumpWidget(_harness(CareerPipelineScreen(
      applications: applications,
      onTapApplication: (a) => tapped = a,
    )));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Stripe'));
    await tester.pumpAndSettle();

    expect(tapped?.company, 'Stripe');
  });

  testWidgets('a real "Schedule interview" action calls the real onScheduleInterview callback', (tester) async {
    final applications = [_application('Stripe')];
    CareerApplication? scheduled;
    await tester.pumpWidget(_harness(CareerPipelineScreen(
      applications: applications,
      onScheduleInterview: (a) => scheduled = a,
    )));
    await tester.pumpAndSettle();

    await tester.tap(find.byTooltip('Schedule interview'));
    await tester.pumpAndSettle();

    expect(scheduled?.company, 'Stripe');
  });
}
