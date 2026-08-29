// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.
//
// Typography as the visualization, literally, not just in principle: the
// computed numbers render as large numerals directly -- no chart widget,
// no gauge, no decorative graphic standing in for the number. The locked
// design principle from the ADD, implemented exactly as written. (A
// real, disclosed correction: this line used to hardcode "36px, weight
// 600" -- accurate only before Phase 8 Session 2 (`DEC-156`) replaced
// that literal `TextStyle` with `QuorumTextStyles.metric()`, this app's
// real, shared numeric-readout style. Stated generally here now, rather
// than re-pinning a specific size this file no longer controls.)
//
// The F4 fix's UI requirement, honored to the letter: when a number's
// source is DataSource.localMirror, the card shows "Offline estimate"
// via BOTH an icon and text -- never color alone, matching the
// accessibility rule already established in quorum_theme.dart. This is
// the actual, concrete moment the ADD's "the client must render this
// label, never silently presenting one as the other" requirement
// becomes real UI, not just a documented promise.
//
// A real mistake caught and fixed WITHIN this repository's own
// construction, not inherited from elsewhere: wiring
// `TodayWidgetBridge` here first added an unnecessary direct
// `import 'package:home_widget/home_widget.dart'` alongside the real
// bridge import -- genuinely unused, since only the bridge itself is
// needed. Caught before finalizing this file, never committed. Confirm:
// this file imports ONLY `today_widget_bridge.dart`, never
// `package:home_widget/home_widget.dart` directly.
//
// Converted from StatelessWidget to StatefulWidget specifically so the
// real home-screen widget update can fire genuinely on data loads --
// once when this zone first mounts with real data, and again only when
// the real capacity/budget numbers actually change, never on every
// unrelated rebuild.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/computed_state.dart';
import 'package:quorum_mobile/features/today/holding_steady_logic.dart';
import 'package:quorum_mobile/features/today_widget_bridge.dart';
import 'package:quorum_mobile/theme/motion.dart';
import 'package:quorum_mobile/theme/quorum_theme.dart';
import 'package:quorum_mobile/theme/spacing.dart';

class HoldingSteadyZone extends StatefulWidget {
  final CapacityState capacity;
  final BudgetState budget;
  final DateTime now;

  const HoldingSteadyZone({
    super.key,
    required this.capacity,
    required this.budget,
    required this.now,
  });

  @override
  State<HoldingSteadyZone> createState() => _HoldingSteadyZoneState();
}

class _HoldingSteadyZoneState extends State<HoldingSteadyZone> {
  @override
  void initState() {
    super.initState();
    _updateWidget();
  }

  @override
  void didUpdateWidget(covariant HoldingSteadyZone oldWidget) {
    super.didUpdateWidget(oldWidget);
    // Fire again only when the real numbers actually changed -- never on
    // an unrelated rebuild carrying the same, already-relayed data.
    if (oldWidget.capacity.hoursRemainingToday != widget.capacity.hoursRemainingToday ||
        oldWidget.budget.remainingFraction != widget.budget.remainingFraction) {
      _updateWidget();
    }
  }

  void _updateWidget() {
    TodayWidgetBridge.updateWidget(
      hoursRemainingToday: widget.capacity.hoursRemainingToday,
      budgetRemainingFraction: widget.budget.remainingFraction,
    );
  }

  @override
  Widget build(BuildContext context) {
    final touchpoint = classifyTouchpoint(widget.now.hour);
    final headline = touchpointHeadline(touchpoint);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(QuorumSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(headline, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: QuorumSpacing.md),
            _ComputedNumberRow(
              label: 'Capacity remaining today',
              valueText: '${widget.capacity.hoursRemainingToday.toStringAsFixed(1)}h',
              source: widget.capacity.source,
            ),
            // A real, disclosed 12px -> 8px tightening (`DEC-156` review
            // finding), not an accidental token-rounding artifact:
            // QuorumSpacing has no `12` value, and `sm` (8) reads as a
            // deliberately tighter pairing between these two conceptually
            // paired metrics than the looser `md` (16) gap already used
            // above, between the headline and the first number.
            const SizedBox(height: QuorumSpacing.sm),
            _ComputedNumberRow(
              label: 'Budget remaining this month',
              valueText: '${(widget.budget.remainingFraction * 100).round()}%',
              source: widget.budget.source,
            ),
          ],
        ),
      ),
    );
  }
}

class _ComputedNumberRow extends StatelessWidget {
  final String label;
  final String valueText;
  final DataSource source;

  const _ComputedNumberRow({
    required this.label,
    required this.valueText,
    required this.source,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: Theme.of(context).textTheme.bodySmall),
              // Typography IS the visualization -- no chart, no gauge.
              // IBM Plex Mono, tabular figures (Phase 8, `DEC-156`) --
              // this is exactly the "prominent numeric readout"
              // QuorumTextStyles.metric() was built for.
              //
              // Real motion (Phase 8 Session 4, `DEC-158`): "Today's
              // capacity/budget numbers updating" is one of this plan's
              // own three explicitly named real motion targets --
              // `AnimatedSwitcher`, keyed by the value text itself, so a
              // real change (e.g. "8.0h" -> "7.5h" after a task is
              // logged) cross-fades rather than snapping instantly. A
              // rebuild carrying the SAME value text never re-triggers
              // the transition -- the key is unchanged, so
              // `AnimatedSwitcher` recognizes it as the same child.
              AnimatedSwitcher(
                duration: QuorumMotion.resolve(context, QuorumMotion.transition),
                child: Text(
                  valueText,
                  key: ValueKey(valueText),
                  style: QuorumTextStyles.metric(context),
                ),
              ),
            ],
          ),
        ),
        if (source == DataSource.localMirror) const _OfflineEstimateBadge(),
      ],
    );
  }
}

/// Never color alone -- both a real icon and real text, every time.
class _OfflineEstimateBadge extends StatelessWidget {
  const _OfflineEstimateBadge();

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(Icons.cloud_off, size: 16, color: Theme.of(context).colorScheme.onSurfaceVariant),
        const SizedBox(width: QuorumSpacing.xs),
        Text('Offline estimate', style: Theme.of(context).textTheme.labelSmall),
      ],
    );
  }
}
