// Real widget tests for features/email/email_workspace_screen.dart
// (`DEC-199`, product rebuild).

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:quorum_mobile/features/email/email_overview_logic.dart';
import 'package:quorum_mobile/features/email/email_workspace_screen.dart';
import 'package:quorum_mobile/theme/quorum_dark_theme.dart';

const _empty = EmailOverviewData(drafts: [], sentHistory: [], knownRecipients: []);

Widget _harness(Future<EmailOverviewData> Function() fetch) {
  return MaterialApp(theme: buildQuorumDarkTheme(), home: EmailWorkspaceScreen(fetch: fetch));
}

void main() {
  testWidgets('a real, honestly empty workspace shows all three honest empty states', (tester) async {
    await tester.pumpWidget(_harness(() async => _empty));
    await tester.pumpAndSettle();

    expect(find.text('Nothing waiting on a reply'), findsOneWidget);
    expect(find.text('No real drafts yet'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('Nothing sent yet'), 300, scrollable: find.byType(Scrollable).first);
    expect(find.text('Nothing sent yet'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('No one you\'ve genuinely emailed yet'), 300, scrollable: find.byType(Scrollable).first);
    expect(find.text('No one you\'ve genuinely emailed yet'), findsOneWidget);
  });

  testWidgets('a real, unreplied sent message shows in both Awaiting reply and Sent history', (tester) async {
    final data = EmailOverviewData(
      drafts: const [],
      sentHistory: [
        SentMessageData(recipient: 'a@x.com', subject: 'a real unreplied subject', sentAt: DateTime(2026, 9, 1), repliedAt: null),
      ],
      knownRecipients: const [],
    );
    await tester.pumpWidget(_harness(() async => data));
    await tester.pumpAndSettle();

    // `DEC-213`'s own redesign added real header content above the
    // sections (the agent name/purpose, the "nothing here is
    // simulated" line), pushing the real Sent History row beyond the
    // default test viewport's render/cache range -- confirmed by
    // isolating against a real, much taller surface (not a logic
    // bug: `scrollUntilVisible` toward the section header alone left
    // it unmounted too, since ensuring the HEADER is visible doesn't
    // guarantee the ROW below it, further down, also is).
    await tester.binding.setSurfaceSize(const Size(400, 3000));
    await tester.pumpAndSettle();
    expect(find.text('a real unreplied subject'), findsNWidgets(2));
    expect(find.text('Awaiting reply'), findsOneWidget);
    addTearDown(() => tester.binding.setSurfaceSize(null));
  });

  testWidgets('a real, replied sent message shows Replied in Sent history, and never in Awaiting reply', (tester) async {
    final data = EmailOverviewData(
      drafts: const [],
      sentHistory: [
        SentMessageData(recipient: 'a@x.com', subject: 'a real replied subject', sentAt: DateTime(2026, 9, 1), repliedAt: DateTime(2026, 9, 2)),
      ],
      knownRecipients: const [],
    );
    await tester.pumpWidget(_harness(() async => data));
    await tester.pumpAndSettle();

    expect(find.text('Nothing waiting on a reply'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('a real replied subject'), 300, scrollable: find.byType(Scrollable).first);
    expect(find.text('a real replied subject'), findsOneWidget);
    expect(find.text('Replied'), findsOneWidget);
  });

  testWidgets('a real draft renders its real recipient, subject, and draft marker', (tester) async {
    final data = EmailOverviewData(
      drafts: [
        EmailDraftData(proposalId: 'p1', createdAt: DateTime(2026, 9, 1), recipient: 'sarah@example.com', subject: 'Re: proposal', draftId: 'draft-abc'),
      ],
      sentHistory: const [],
      knownRecipients: const [],
    );
    await tester.pumpWidget(_harness(() async => data));
    await tester.pumpAndSettle();

    expect(find.text('Re: proposal'), findsOneWidget);
    expect(find.text('To: sarah@example.com'), findsOneWidget);
    expect(find.text('Draft'), findsOneWidget);
  });

  testWidgets('a real draft with no subject shows an honest placeholder, never a blank row', (tester) async {
    final data = EmailOverviewData(
      drafts: [
        EmailDraftData(proposalId: 'p1', createdAt: DateTime(2026, 9, 1), recipient: 'a@x.com', subject: null, draftId: 'draft-xyz'),
      ],
      sentHistory: const [],
      knownRecipients: const [],
    );
    await tester.pumpWidget(_harness(() async => data));
    await tester.pumpAndSettle();

    expect(find.text('(no subject)'), findsOneWidget);
  });

  testWidgets('a real known recipient shows its real message count', (tester) async {
    final data = EmailOverviewData(
      drafts: const [],
      sentHistory: const [],
      knownRecipients: [
        KnownRecipientData(recipient: 'sarah@example.com', lastContactedAt: DateTime(2026, 9, 1), messageCount: 3),
      ],
    );
    await tester.pumpWidget(_harness(() async => data));
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(find.text('sarah@example.com'), 300, scrollable: find.byType(Scrollable).first);
    expect(find.text('sarah@example.com'), findsOneWidget);
    expect(find.textContaining('3 messages'), findsOneWidget);
  });

  testWidgets('shows a real, honest error state on a real fetch failure, not a crash', (tester) async {
    await tester.pumpWidget(_harness(() async => throw Exception('network down')));
    await tester.pumpAndSettle();

    expect(find.textContaining('network down'), findsOneWidget);
    expect(find.text('Try again'), findsOneWidget);
  });

  testWidgets('tapping Try again genuinely retries without throwing the real setState/Future assertion', (tester) async {
    var attempt = 0;
    await tester.pumpWidget(_harness(() async {
      attempt++;
      if (attempt == 1) throw Exception('network down');
      return _empty;
    }));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Try again'));
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.text('Nothing waiting on a reply'), findsOneWidget);
  });
}
