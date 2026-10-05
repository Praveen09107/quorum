// Real tests for the `DEC-189` shared widget kit's pure logic and for
// the honesty invariants the kit exists to make easy to honor.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:quorum_mobile/features/gate_reveal/gate_reveal_logic.dart';
import 'package:quorum_mobile/theme/quorum_dark_theme.dart';
import 'package:quorum_mobile/theme/quorum_kit.dart';

void main() {
  group('evidenceAppearance', () {
    test('gives each of the three evidence states a distinct color AND icon', () {
      // The single most load-bearing invariant in this file. If two
      // states ever shared a color, `no_data_found` could be read as a
      // pass or a fail -- the exact collapse `CLAUDE.md` forbids. If
      // they shared an icon, color would be carrying the meaning
      // alone, which ADD §12.4 forbids. Both must hold.
      final appearances = EvidenceVisualState.values.map(evidenceAppearance).toList();

      final colors = appearances.map((a) => a.color.toARGB32()).toSet();
      expect(colors.length, EvidenceVisualState.values.length,
          reason: 'two evidence states share a color');

      final icons = appearances.map((a) => a.icon.codePoint).toSet();
      expect(icons.length, EvidenceVisualState.values.length,
          reason: 'two evidence states share an icon');
    });

    test('maps each state to its intended status color', () {
      expect(evidenceAppearance(EvidenceVisualState.positive).color, QuorumDarkStatus.verified);
      expect(evidenceAppearance(EvidenceVisualState.negative).color, QuorumDarkStatus.critical);
      expect(evidenceAppearance(EvidenceVisualState.uncertain).color, QuorumDarkStatus.needsAttention);
    });

    test('labels no_data_found honestly, never as a pass or a fail', () {
      expect(evidenceAppearance(EvidenceVisualState.uncertain).label, 'No data found');
    });

    test('an unrecognized raw evidence_state resolves to uncertain, never positive', () {
      // Composed with the already-real visualStateForEvidence to prove
      // the full raw-string-to-appearance path fails in the safe
      // direction.
      final appearance = evidenceAppearance(visualStateForEvidence('some_future_value'));
      expect(appearance.color, QuorumDarkStatus.needsAttention);
      expect(appearance.color, isNot(QuorumDarkStatus.verified));
    });
  });

  group('QuorumDarkStatus', () {
    test('all four status colors are genuinely distinct', () {
      final colors = {
        QuorumDarkStatus.verified.toARGB32(),
        QuorumDarkStatus.needsAttention.toARGB32(),
        QuorumDarkStatus.critical.toARGB32(),
        QuorumDarkStatus.neutral.toARGB32(),
      };
      expect(colors.length, 4);
    });

    test('every status color is legible against the dark ground', () {
      // A real regression guard against the specific mistake this
      // theme was created to avoid: the light theme's status colors
      // (green 800, amber 800, red 800) were tuned for contrast
      // against white and genuinely do not read on near-black. A
      // luminance floor catches any future retune that drifts back
      // toward those values.
      for (final color in [
        QuorumDarkStatus.verified,
        QuorumDarkStatus.needsAttention,
        QuorumDarkStatus.critical,
        QuorumDarkStatus.neutral,
      ]) {
        expect(color.computeLuminance(), greaterThan(0.15),
            reason: '$color is too dark to read on QuorumDarkGround.base');
      }
    });
  });

  group('EvidenceRow', () {
    testWidgets('renders the claim and the validator name when resolved', (tester) async {
      await tester.pumpWidget(_host(const EvidenceRow(
        validatorName: 'recipient_check',
        claim: 'Recipient is a known contact',
        state: EvidenceVisualState.positive,
        elapsedMs: 12,
      )));

      expect(find.text('recipient_check'), findsOneWidget);
      expect(find.text('Recipient is a known contact'), findsOneWidget);
      expect(find.text('12ms'), findsOneWidget);
      expect(find.byIcon(Icons.check_circle_rounded), findsOneWidget);
    });

    testWidgets('pending shows a spinner and never an evidence icon', (tester) async {
      // "Has not reported yet" is a transport fact, not a finding --
      // rendering it with any of the three evidence icons would assert
      // a result the system does not have.
      await tester.pumpWidget(_host(const EvidenceRow(
        validatorName: 'pii_leak_check',
        claim: 'unused while pending',
        pending: true,
      )));

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.text('Checking...'), findsOneWidget);
      expect(find.byIcon(Icons.check_circle_rounded), findsNothing);
      expect(find.byIcon(Icons.cancel_rounded), findsNothing);
      expect(find.byIcon(Icons.help_rounded), findsNothing);
    });
  });

  group('LiveDot', () {
    testWidgets('does not animate when inactive', (tester) async {
      await tester.pumpWidget(_host(const LiveDot(active: false)));
      // A pulsing dot with nothing in flight would be a small lie
      // about system state. pumpAndSettle completing proves no
      // animation is running -- it times out on a repeating one.
      await tester.pumpAndSettle();
      expect(find.byType(LiveDot), findsOneWidget);
    });
  });

  group('HonestEmptyState', () {
    testWidgets('renders a real headline and detail rather than a bare zero', (tester) async {
      await tester.pumpWidget(_host(const HonestEmptyState(
        icon: Icons.inbox_outlined,
        headline: 'No drafts yet',
        detail: 'Quorum creates a draft when you ask it to reply to someone.',
      )));

      expect(find.text('No drafts yet'), findsOneWidget);
      expect(find.textContaining('Quorum creates a draft'), findsOneWidget);
      expect(find.text('0'), findsNothing);
    });
  });

  group('RetryErrorState', () {
    testWidgets('shows the real failure message and invokes the retry', (tester) async {
      var retried = 0;
      await tester.pumpWidget(_host(RetryErrorState(
        message: 'Connection refused',
        onRetry: () => retried++,
      )));

      // The real message, not a generic apology a user cannot act on.
      expect(find.text('Connection refused'), findsOneWidget);
      await tester.tap(find.text('Try again'));
      expect(retried, 1);
    });
  });
}

Widget _host(Widget child) => MaterialApp(
      theme: buildQuorumDarkTheme(),
      home: Scaffold(body: Center(child: child)),
    );
