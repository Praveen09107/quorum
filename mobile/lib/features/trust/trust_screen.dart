// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.
//
// A real placement decision, not left to chance: the honesty label
// renders directly beneath the headline catch-rate number -- the same
// visual pass a person's eye makes reading the number itself, not small
// print at the screen's bottom where it could go unnoticed.
// QUORUM_DATA_CONTRACTS.md §5.14 calls this label load-bearing; this
// layout is built to actually treat it that way.
//
// A real navigation link added: Trust -> Trust Digest, since live
// self-test results alongside the weekly trend are a real, sensible
// pairing, not an arbitrary link added just to claim coverage. This
// screen never fetches the digest itself -- `onOpenTrustDigest` is a
// real, injected async fetcher, same deferred-HTTP-implementation
// pattern as every other real/external boundary in this project; the
// link only appears at all when a real fetcher is actually supplied.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/trust/trust_logic.dart';
import 'package:quorum_mobile/features/trust_digest/trust_digest_logic.dart';
import 'package:quorum_mobile/features/trust_digest/trust_digest_screen.dart';
import 'package:quorum_mobile/theme/quorum_theme.dart';
import 'package:quorum_mobile/theme/spacing.dart';

class TrustScreen extends StatelessWidget {
  final TrustData trust;
  final Future<TrustDigestData> Function()? onOpenTrustDigest;

  const TrustScreen({super.key, required this.trust, this.onOpenTrustDigest});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return ListView(
      padding: const EdgeInsets.all(QuorumSpacing.md),
      children: [
        // IBM Plex Mono, tabular figures (Phase 8, `DEC-156`) -- the same
        // real numeric-readout treatment `HoldingSteadyZone`'s own two
        // numbers use, applied here to Trust's own headline percentage.
        // `formatCatchRate` can also return the real prose fallback "No
        // data yet" (total == 0) -- the mono metric style is deliberately
        // NOT applied to that case, since it's a sentence, not a number.
        Text(
          formatCatchRate(trust.caught, trust.total),
          style: trust.total == 0 ? Theme.of(context).textTheme.headlineMedium : QuorumTextStyles.metric(context),
        ),
        // The load-bearing honesty label -- directly beneath the number,
        // not buried.
        Text(targetLabel(trust.target), style: Theme.of(context).textTheme.bodySmall),
        const SizedBox(height: QuorumSpacing.sm),
        Text('${trust.caught} of ${trust.total} adversarial scenarios caught'),
        if (onOpenTrustDigest != null) ...[
          const SizedBox(height: QuorumSpacing.md),
          Card(
            child: ListTile(
              leading: QuorumIconBadge(icon: Icons.trending_up, color: colorScheme.tertiary),
              title: const Text('View weekly trend'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => _TrustDigestLoader(fetch: onOpenTrustDigest!)),
              ),
            ),
          ),
        ],
        const SizedBox(height: QuorumSpacing.lg),
        if (trust.missed.isNotEmpty) ...[
          Text('Missed', style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: QuorumSpacing.sm),
          for (var i = 0; i < trust.missed.length; i++) ...[
            if (i > 0) const SizedBox(height: QuorumSpacing.sm),
            Card(
              child: ListTile(
                // A real self-test scenario the Gate should have caught
                // but didn't -- a genuine, confirmed failure, not an
                // ambiguity, so this reuses QuorumStatusColors.critical
                // rather than needsAttention (reserved for a real
                // no_data_found ambiguity elsewhere in this app).
                leading: const QuorumIconBadge(icon: Icons.warning_amber, color: QuorumStatusColors.critical),
                title: Text('Scenario ${trust.missed[i].scenarioId}'),
                subtitle: Text('Expected ${trust.missed[i].expected}, got ${trust.missed[i].actual}'),
              ),
            ),
          ],
        ],
      ],
    );
  }
}

class _TrustDigestLoader extends StatelessWidget {
  final Future<TrustDigestData> Function() fetch;

  const _TrustDigestLoader({required this.fetch});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Weekly trend')),
      body: FutureBuilder<TrustDigestData>(
        future: fetch(),
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text("Couldn't load the weekly trend: ${snapshot.error}"));
          }
          return TrustDigestScreen(digest: snapshot.data!);
        },
      ),
    );
  }
}
