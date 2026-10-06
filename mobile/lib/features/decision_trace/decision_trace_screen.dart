// The real Decision Trace screen (`DEC-201`, product rebuild) -- "any
// past action, replayed," named in the original rebuild plan as the
// judge-facing "proof it's real" screen. `GET /actions/{id}/status`
// has carried everything this screen needs (the real, recorded Gate
// timeline, the real pre-revision payload) since `DEC-189` Block B --
// this is its first real mobile caller.
//
// Reuses the live pipeline's own real event parser and row widget
// (`gate_pipeline_logic.dart`'s `GateEvent`/`reducePipelineEvents`,
// `gate_pipeline_screen.dart`'s now-public `PipelineRowTile`) rather
// than a second, parallel rendering of the identical real event
// vocabulary -- a stored, replayed timeline and a live one are the
// same real shape, just read from a database row instead of a stream.

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import 'package:quorum_mobile/api/action_status_api.dart';
import 'package:quorum_mobile/features/decision_trace/decision_trace_logic.dart';
import 'package:quorum_mobile/features/gate_pipeline/artifact_links.dart';
import 'package:quorum_mobile/features/gate_pipeline/gate_pipeline_logic.dart';
import 'package:quorum_mobile/features/gate_pipeline/gate_pipeline_screen.dart';
import 'package:quorum_mobile/theme/glass.dart';
import 'package:quorum_mobile/theme/quorum_dark_theme.dart';
import 'package:quorum_mobile/theme/quorum_kit.dart';
import 'package:quorum_mobile/theme/spacing.dart';

class DecisionTraceScreen extends StatefulWidget {
  final String proposalId;
  final ActionStatusFetcher fetch;

  const DecisionTraceScreen({super.key, required this.proposalId, required this.fetch});

  @override
  State<DecisionTraceScreen> createState() => _DecisionTraceScreenState();
}

class _DecisionTraceScreenState extends State<DecisionTraceScreen> {
  late Future<ActionStatusData> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.fetch(widget.proposalId);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Decision trace')),
      body: QuorumAmbientBackground(
        child: SafeArea(
          child: FutureBuilder<ActionStatusData>(
            future: _future,
            builder: (context, snapshot) {
              if (snapshot.connectionState != ConnectionState.done) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snapshot.hasError) {
                return Center(
                  child: RetryErrorState(
                    message: 'Could not load this action -- ${snapshot.error}',
                    onRetry: () => setState(() {
                      _future = widget.fetch(widget.proposalId);
                    }),
                  ),
                );
              }
              final data = snapshot.data!;
              final rawTimeline = data.timeline;
              final link = artifactLinkFor(data.artifact);
              return ListView(
                padding: const EdgeInsets.all(QuorumSpacing.md),
                children: [
                  _HeaderCard(data: data),
                  const SizedBox(height: QuorumSpacing.md),
                  if (link != null) ...[
                    OutlinedButton.icon(
                      onPressed: () => _openArtifactLink(context, link),
                      icon: const Icon(Icons.open_in_new_rounded, size: 16),
                      label: Text(link.label),
                    ),
                    const SizedBox(height: QuorumSpacing.md),
                  ],
                  if (data.preRevisionPayload != null) ...[
                    const SectionHeader(label: 'What the Gate changed', accent: QuorumDarkStatus.needsAttention),
                    _RevisionDiffPanel(
                      before: data.preRevisionPayload!,
                      after: data.payload,
                    ),
                    const SizedBox(height: QuorumSpacing.md),
                  ],
                  const SectionHeader(label: 'How the Gate reviewed this', accent: QuorumDarkStatus.verified),
                  if (rawTimeline == null)
                    const HonestEmptyState(
                      icon: Icons.history_toggle_off_rounded,
                      headline: 'Not recorded for this action',
                      detail: 'This action resolved before timeline recording existed -- nothing was silently dropped, it genuinely was never captured.',
                    )
                  else
                    _TimelineSection(rawTimeline: rawTimeline),
                ],
              );
            },
          ),
        ),
      ),
    );
  }

  Future<void> _openArtifactLink(BuildContext context, ArtifactLink link) async {
    final uri = Uri.parse(link.url);
    final opened = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (!opened && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Couldn't open ${link.label.toLowerCase()} -- no app available for this link.")),
      );
    }
  }
}

class _HeaderCard extends StatelessWidget {
  final ActionStatusData data;

  const _HeaderCard({required this.data});

  @override
  Widget build(BuildContext context) {
    return GlassPanel(
      accent: _stakesColor(data.stakes),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            formatActionType(data.actionType),
            style: Theme.of(context).textTheme.titleMedium?.copyWith(color: QuorumDarkGround.textPrimary),
          ),
          const SizedBox(height: QuorumSpacing.sm),
          Row(
            children: [
              StatusPill(label: data.stakes, icon: Icons.layers_rounded, color: _stakesColor(data.stakes)),
              const SizedBox(width: QuorumSpacing.sm),
              if (data.outcome != null)
                StatusPill(label: _outcomeLabel(data.outcome!), icon: _outcomeIcon(data.outcome!), color: _outcomeColor(data.outcome!)),
            ],
          ),
          if (data.resolvedAt != null) ...[
            const SizedBox(height: QuorumSpacing.sm),
            Text('Resolved ${data.resolvedAt!.toLocal().toIso8601String().split('.').first}', style: QuorumMono.detail(context)),
          ],
        ],
      ),
    );
  }

  Color _stakesColor(String tier) {
    switch (tier) {
      case 'S3':
        return QuorumDarkStatus.critical;
      case 'S2':
        return QuorumDarkStatus.needsAttention;
      default:
        return QuorumDarkStatus.verified;
    }
  }

  String _outcomeLabel(String outcome) {
    if (outcome.isEmpty) return 'Logged';
    return outcome.split('_').where((w) => w.isNotEmpty).map((w) => w[0].toUpperCase() + w.substring(1)).join(' ');
  }

  IconData _outcomeIcon(String outcome) {
    switch (outcome) {
      case 'approved_unchanged':
        return Icons.check_circle_outline;
      case 'caught_by_gate':
        return Icons.shield_outlined;
      case 'corrected_by_user':
        return Icons.edit_outlined;
      case 'rejected_by_user':
        return Icons.block_outlined;
      default:
        return Icons.circle_outlined;
    }
  }

  Color _outcomeColor(String outcome) {
    switch (outcome) {
      case 'approved_unchanged':
        return QuorumDarkStatus.verified;
      case 'caught_by_gate':
      case 'rejected_by_user':
        return QuorumDarkStatus.needsAttention;
      default:
        return QuorumDarkStatus.neutral;
    }
  }
}

class _RevisionDiffPanel extends StatelessWidget {
  final Map<String, dynamic> before;
  final Map<String, dynamic> after;

  const _RevisionDiffPanel({required this.before, required this.after});

  @override
  Widget build(BuildContext context) {
    final diff = computePayloadDiff(before, after);
    if (diff.isEmpty) {
      // A real, honest edge case: `pre_revision_payload` is present
      // (the Judge was given the chance to revise) but every real
      // value came back identical -- never pretend a change happened
      // that didn't.
      return const HonestEmptyState(
        icon: Icons.fact_check_outlined,
        headline: 'The Judge reviewed this without changing it',
        detail: 'A real revision was recorded, but no field\'s value actually differs.',
      );
    }
    return GlassPanel(
      accent: QuorumDarkStatus.needsAttention,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          for (var i = 0; i < diff.length; i++) ...[
            if (i > 0) const Divider(height: QuorumSpacing.md),
            Text(diff[i].key, style: Theme.of(context).textTheme.titleSmall?.copyWith(color: QuorumDarkGround.textPrimary)),
            const SizedBox(height: 4),
            Text('Before: ${formatDiffValue(diff[i].before)}', style: QuorumMono.detail(context, color: QuorumDarkStatus.critical)),
            Text('After: ${formatDiffValue(diff[i].after)}', style: QuorumMono.detail(context, color: QuorumDarkStatus.verified)),
          ],
        ],
      ),
    );
  }
}

class _TimelineSection extends StatelessWidget {
  final List<dynamic> rawTimeline;

  const _TimelineSection({required this.rawTimeline});

  @override
  Widget build(BuildContext context) {
    final List<GateEvent> events;
    try {
      events = rawTimeline.map((raw) => GateEvent.fromMap(raw as Map<String, dynamic>)).toList();
    } catch (e) {
      // A genuinely malformed stored record -- honest, not a crash,
      // and deliberately NOT `RetryErrorState`: re-fetching the exact
      // same already-malformed row would never fix this, so a "Try
      // again" button here would be a dishonest affordance.
      return HonestEmptyState(
        icon: Icons.error_outline_rounded,
        headline: "This action's recorded timeline could not be read",
        detail: '$e',
      );
    }
    final view = reducePipelineEvents(events);
    if (view.rows.isEmpty) {
      return const HonestEmptyState(
        icon: Icons.history_toggle_off_rounded,
        headline: 'Nothing real to replay',
        detail: 'A timeline was recorded, but it carried no real stage events.',
      );
    }
    return Column(
      children: [
        for (final row in view.rows) PipelineRowTile(key: ValueKey(row.id), row: row),
      ],
    );
  }
}
