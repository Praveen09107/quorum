// The real, full per-scenario verdict replay (`DEC-204`, product
// rebuild) -- the plan's own named "Gate -- Self-test" screen item:
// "Every scenario, its full GateVerdict (currently computed then
// thrown away), pass/fail." The backend side of that was already
// fixed by `DEC-193` (`_serialize_scenario_result()` now includes the
// complete real verdict); this screen is the first real mobile reader
// of it -- `trust_api.dart` previously decoded the response and
// silently dropped the whole `verdict` key.
//
// Deliberately reuses `FindingRow`/`StageBSection` from `gate_reveal_
// screen.dart` rather than a second, parallel rendering of the
// identical real `Finding`/`Objection` shape -- both were already
// made public for exactly this kind of second real reuse.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/gate_reveal/gate_reveal_logic.dart';
import 'package:quorum_mobile/features/gate_reveal/gate_reveal_screen.dart';
import 'package:quorum_mobile/features/trust/trust_logic.dart';
import 'package:quorum_mobile/theme/quorum_theme.dart';
import 'package:quorum_mobile/theme/spacing.dart';

class ScenarioVerdictScreen extends StatelessWidget {
  final ScenarioResultData result;

  const ScenarioVerdictScreen({super.key, required this.result});

  @override
  Widget build(BuildContext context) {
    final verdict = result.verdict;
    final stageB = summarizeStageB(verdict.objections);
    final colorScheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(title: Text('Scenario ${result.scenarioId}')),
      body: ListView(
        padding: const EdgeInsets.all(QuorumSpacing.md),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(QuorumSpacing.md),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      QuorumIconBadge(
                        icon: result.passed ? Icons.check_circle : Icons.warning_amber,
                        color: result.passed ? QuorumStatusColors.verified : QuorumStatusColors.critical,
                      ),
                      const SizedBox(width: QuorumSpacing.sm),
                      Expanded(
                        child: Text(
                          result.passed ? 'The Gate caught this real scenario' : 'The Gate missed this real scenario',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: QuorumSpacing.sm),
                  Text('Expected: ${result.expected}'),
                  Text('Actual: ${result.actual}'),
                  const SizedBox(height: QuorumSpacing.sm),
                  Text('Real decision: ${verdict.decision}', style: Theme.of(context).textTheme.bodyMedium),
                  if (verdict.revisionCount > 0)
                    Text(
                      'The Judge revised this proposal before deciding.',
                      style: TextStyle(color: colorScheme.tertiary),
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(height: QuorumSpacing.lg),
          if (verdict.findings.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: QuorumSpacing.sm),
              child: Text('No real Stage A findings were recorded for this scenario.'),
            )
          else ...[
            Text('Stage A -- what the real checks found', style: Theme.of(context).textTheme.titleSmall),
            for (final finding in verdict.findings) FindingRow(finding: finding),
          ],
          const SizedBox(height: QuorumSpacing.lg),
          if (stageBRan(verdict.objections)) ...[
            Text('Stage B -- the real Critic and Judge', style: Theme.of(context).textTheme.titleSmall),
            StageBSection(summary: stageB),
          ] else
            const Padding(
              padding: EdgeInsets.symmetric(vertical: QuorumSpacing.sm),
              child: Text(
                'Stage B never ran for this scenario -- a real, structural fact for an S0/S1 proposal, not a gap.',
              ),
            ),
        ],
      ),
    );
  }
}
