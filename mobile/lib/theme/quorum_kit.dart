// The real shared widget kit for the `DEC-189` product rebuild.
//
// WHY THIS FILE EXISTS: the rebuild replaces roughly twenty screens in
// a genuinely tight window, and the only way that is feasible is if
// each screen is composition rather than design. Everything here is a
// piece more than one screen needs. Nothing here is screen-specific --
// a widget used by exactly one screen belongs in that screen's own
// folder, not in the kit.
//
// EVERY PIECE IN THIS FILE HONORS THE SAME TWO RULES, which survive the
// visual supersession `quorum_dark_theme.dart` describes:
//   1. Color never carries meaning alone. Every status-bearing widget
//      here renders a distinct ICON as well as a distinct color.
//   2. Nothing fabricates data. [HonestEmptyState] exists specifically
//      so a screen with no real data shows an honest absence instead of
//      a zero that looks like a measurement.

import 'package:flutter/material.dart';

import '../features/gate_reveal/gate_reveal_logic.dart';
import 'agent_identity.dart';
import 'glass.dart';
import 'quorum_dark_theme.dart';
import 'spacing.dart';

/// Resolves the real three-valued evidence state to its color and its
/// genuinely distinct icon, together, so no caller can accidentally take
/// the color without the icon.
///
/// Reuses the already-real, already-tested [visualStateForEvidence] from
/// `gate_reveal_logic.dart` rather than reimplementing the mapping --
/// that function is the single source of truth for how a raw
/// `evidence_state` string becomes a visual state, including its
/// deliberate "unrecognized value is treated as uncertain, never as a
/// pass" fallback.
({Color color, IconData icon, String label}) evidenceAppearance(EvidenceVisualState state) {
  switch (state) {
    case EvidenceVisualState.positive:
      return (color: QuorumDarkStatus.verified, icon: Icons.check_circle_rounded, label: 'Verified');
    case EvidenceVisualState.negative:
      return (color: QuorumDarkStatus.critical, icon: Icons.cancel_rounded, label: 'Contradicted');
    case EvidenceVisualState.uncertain:
      return (color: QuorumDarkStatus.needsAttention, icon: Icons.help_rounded, label: 'No data found');
  }
}

/// One Stage A validator finding, rendered as a row.
///
/// This is the single most important widget in the rebuild: watching
/// these resolve one at a time is the interaction
/// `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §12.1 named as the thing
/// this product should own, and which had never been built.
///
/// [pending] renders the pre-resolution state. It is deliberately NOT a
/// fourth evidence value -- it means "this check has not reported yet,"
/// which is a transport fact, not a finding. Collapsing it into
/// `no_data_found` would be exactly the three-valued violation this
/// project forbids: "we haven't asked yet" and "we asked and found
/// nothing" are genuinely different.
class EvidenceRow extends StatelessWidget {
  final String validatorName;
  final String claim;
  final EvidenceVisualState? state;
  final int? elapsedMs;
  final bool pending;

  const EvidenceRow({
    super.key,
    required this.validatorName,
    required this.claim,
    this.state,
    this.elapsedMs,
    this.pending = false,
  });

  @override
  Widget build(BuildContext context) {
    final appearance = state == null ? null : evidenceAppearance(state!);
    final color = appearance?.color ?? QuorumDarkStatus.neutral;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: QuorumSpacing.sm),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 22,
            height: 22,
            child: pending
                ? const Padding(
                    padding: EdgeInsets.all(3),
                    child: CircularProgressIndicator(strokeWidth: 2, color: QuorumDarkStatus.neutral),
                  )
                : Icon(appearance?.icon ?? Icons.remove_rounded, size: 20, color: color),
          ),
          const SizedBox(width: QuorumSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Flexible(
                      child: Text(
                        validatorName,
                        style: QuorumMono.detail(context, color: QuorumDarkGround.textSecondary),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    if (elapsedMs != null) ...[
                      const SizedBox(width: QuorumSpacing.sm),
                      Text('${elapsedMs}ms', style: QuorumMono.detail(context)),
                    ],
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  pending ? 'Checking...' : claim,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: pending ? QuorumDarkGround.textTertiary : QuorumDarkGround.textPrimary,
                      ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// A compact status chip. Always renders icon + text, never color alone.
class StatusPill extends StatelessWidget {
  final String label;
  final IconData icon;
  final Color color;
  final bool emphasized;

  const StatusPill({
    super.key,
    required this.label,
    required this.icon,
    required this.color,
    this.emphasized = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: emphasized ? 0.22 : 0.12),
        borderRadius: BorderRadius.circular(QuorumRadius.pill),
        border: Border.all(color: color.withValues(alpha: emphasized ? 0.7 : 0.35)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 13, color: color),
          const SizedBox(width: 5),
          Text(
            label,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: color,
                  fontWeight: FontWeight.w600,
                ),
          ),
        ],
      ),
    );
  }
}

/// An agent's identity as a chip: its icon in its accent, plus its name.
class AgentBadge extends StatelessWidget {
  final QuorumAgent agent;
  final bool compact;

  const AgentBadge({super.key, required this.agent, this.compact = false});

  @override
  Widget build(BuildContext context) {
    final identity = identityOf(agent);
    if (compact) {
      return Container(
        width: 30,
        height: 30,
        decoration: BoxDecoration(
          color: identity.accent.withValues(alpha: 0.14),
          shape: BoxShape.circle,
          border: Border.all(color: identity.accent.withValues(alpha: 0.4)),
        ),
        child: Icon(identity.icon, size: 16, color: identity.accent),
      );
    }
    return StatusPill(label: identity.name, icon: identity.icon, color: identity.accent);
  }
}

/// A pulsing dot, shown only where something is GENUINELY in flight.
///
/// Deliberately never decorative: a live indicator that pulses when
/// nothing is happening is a small lie about the system's state, and
/// this app's whole thesis is about not telling those. Callers pass
/// [active] from real state, and the dot renders flat and grey when
/// false rather than disappearing, so the position stays stable.
class LiveDot extends StatefulWidget {
  final bool active;
  final Color color;
  final double size;

  const LiveDot({super.key, required this.active, this.color = QuorumDarkStatus.verified, this.size = 8});

  @override
  State<LiveDot> createState() => _LiveDotState();
}

class _LiveDotState extends State<LiveDot> with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1400),
  );

  @override
  void initState() {
    super.initState();
    if (widget.active) _controller.repeat(reverse: true);
  }

  @override
  void didUpdateWidget(LiveDot oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.active && !_controller.isAnimating) {
      _controller.repeat(reverse: true);
    } else if (!widget.active && _controller.isAnimating) {
      _controller.stop();
      _controller.value = 0;
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // Respect the real OS-level reduced-motion setting rather than
    // pulsing regardless -- a looping animation is exactly the kind a
    // user who has asked for less motion is asking not to see.
    final reduceMotion = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
    final color = widget.active ? widget.color : QuorumDarkStatus.neutral;

    if (!widget.active || reduceMotion) {
      return _dot(color, glow: widget.active ? 0.35 : 0.0);
    }

    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) => _dot(color, glow: 0.2 + (_controller.value * 0.6)),
    );
  }

  Widget _dot(Color color, {required double glow}) => Container(
        width: widget.size,
        height: widget.size,
        decoration: BoxDecoration(
          color: color,
          shape: BoxShape.circle,
          boxShadow: glow > 0
              ? [BoxShadow(color: color.withValues(alpha: glow), blurRadius: 8, spreadRadius: 2)]
              : null,
        ),
      );
}

/// A real metric readout: a large mono number, a label, and -- crucially
/// -- an optional [source] line saying where the number came from.
///
/// [source] is not decoration. `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md`
/// requires that a computed number disclose its own provenance, so a
/// user can tell a measured value from a derived one. Keeping the field
/// on the shared widget means a screen has to actively pass null to
/// omit it, rather than simply forgetting it exists.
class MetricTile extends StatelessWidget {
  final String value;
  final String label;
  final String? source;
  final Color? accent;
  final IconData? icon;
  final VoidCallback? onWhy;

  const MetricTile({
    super.key,
    required this.value,
    required this.label,
    this.source,
    this.accent,
    this.icon,
    this.onWhy,
  });

  @override
  Widget build(BuildContext context) {
    final color = accent ?? QuorumDarkGround.textPrimary;
    return Container(
      padding: const EdgeInsets.all(QuorumSpacing.md),
      decoration: solidPanelDecoration(accent: accent),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              if (icon != null) ...[
                Icon(icon, size: 15, color: color.withValues(alpha: 0.8)),
                const SizedBox(width: 6),
              ],
              Expanded(
                child: Text(
                  label.toUpperCase(),
                  style: QuorumMono.label(context),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              if (onWhy != null) WhyChip(onTap: onWhy!),
            ],
          ),
          const SizedBox(height: QuorumSpacing.sm),
          Text(value, style: QuorumMono.metric(context, color: color)),
          if (source != null) ...[
            const SizedBox(height: 2),
            Text(source!, style: QuorumMono.detail(context)),
          ],
        ],
      ),
    );
  }
}

/// The "why?" affordance. Specified in the ADD and never built -- a user
/// should always be able to ask where a number came from.
class WhyChip extends StatelessWidget {
  final VoidCallback onTap;

  const WhyChip({super.key, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(QuorumRadius.pill),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.help_outline_rounded, size: 12, color: QuorumDarkGround.textTertiary),
            const SizedBox(width: 3),
            Text('why', style: QuorumMono.detail(context)),
          ],
        ),
      ),
    );
  }
}

/// An honest empty state.
///
/// Exists as a shared piece specifically to make the honest option the
/// easy one. The tempting alternative -- rendering a `0`, or an empty
/// chart with axes -- reads as a measurement and is a quiet lie when
/// the truth is that there is nothing to measure. This widget says so
/// in words instead.
class HonestEmptyState extends StatelessWidget {
  final IconData icon;
  final String headline;

  /// The honest detail: what is actually absent, and why that is or is
  /// not expected. Avoid "Nothing here yet!" -- say what would make
  /// something appear.
  final String detail;
  final Widget? action;

  const HonestEmptyState({
    super.key,
    required this.icon,
    required this.headline,
    required this.detail,
    this.action,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: QuorumSpacing.lg, vertical: QuorumSpacing.xl),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 34, color: QuorumDarkGround.textTertiary),
          const SizedBox(height: QuorumSpacing.md),
          Text(
            headline,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(color: QuorumDarkGround.textSecondary),
          ),
          const SizedBox(height: QuorumSpacing.xs),
          Text(
            detail,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: QuorumDarkGround.textTertiary),
          ),
          if (action != null) ...[const SizedBox(height: QuorumSpacing.md), action!],
        ],
      ),
    );
  }
}

/// A real error state with a real retry. Shows the actual failure rather
/// than a generic apology, because a user who can see "connection
/// refused" can act on it and a user who sees "Something went wrong"
/// cannot.
class RetryErrorState extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;

  const RetryErrorState({super.key, required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(QuorumSpacing.lg),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.error_outline_rounded, size: 30, color: QuorumDarkStatus.critical),
          const SizedBox(height: QuorumSpacing.sm),
          Text(
            message,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: QuorumDarkGround.textSecondary),
          ),
          const SizedBox(height: QuorumSpacing.md),
          OutlinedButton.icon(
            onPressed: onRetry,
            icon: const Icon(Icons.refresh_rounded, size: 16),
            label: const Text('Try again'),
          ),
        ],
      ),
    );
  }
}

/// A section heading with an uppercase mono label and an optional
/// trailing action, used to structure every long screen in the rebuild.
class SectionHeader extends StatelessWidget {
  final String label;
  final Widget? trailing;
  final Color? accent;

  const SectionHeader({super.key, required this.label, this.trailing, this.accent});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: QuorumSpacing.sm, top: QuorumSpacing.lg),
      child: Row(
        children: [
          if (accent != null) ...[
            Container(width: 3, height: 13, color: accent),
            const SizedBox(width: QuorumSpacing.sm),
          ],
          Expanded(child: Text(label.toUpperCase(), style: QuorumMono.label(context))),
          if (trailing != null) trailing!,
        ],
      ),
    );
  }
}
