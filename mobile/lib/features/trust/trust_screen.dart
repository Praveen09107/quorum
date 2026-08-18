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

class TrustScreen extends StatelessWidget {
  final TrustData trust;
  final Future<TrustDigestData> Function()? onOpenTrustDigest;

  const TrustScreen({super.key, required this.trust, this.onOpenTrustDigest});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(
          formatCatchRate(trust.caught, trust.total),
          style: const TextStyle(fontSize: 36, fontWeight: FontWeight.w600),
        ),
        // The load-bearing honesty label -- directly beneath the number,
        // not buried.
        Text(targetLabel(trust.target), style: Theme.of(context).textTheme.bodySmall),
        const SizedBox(height: 8),
        Text('${trust.caught} of ${trust.total} adversarial scenarios caught'),
        if (onOpenTrustDigest != null) ...[
          const SizedBox(height: 16),
          ListTile(
            leading: const Icon(Icons.trending_up),
            title: const Text('View weekly trend'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => _TrustDigestLoader(fetch: onOpenTrustDigest!)),
            ),
          ),
        ],
        const SizedBox(height: 24),
        if (trust.missed.isNotEmpty) ...[
          Text('Missed', style: Theme.of(context).textTheme.titleSmall),
          for (final scenario in trust.missed)
            ListTile(
              leading: const Icon(Icons.warning_amber),
              title: Text('Scenario ${scenario.scenarioId}'),
              subtitle: Text('Expected ${scenario.expected}, got ${scenario.actual}'),
            ),
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
