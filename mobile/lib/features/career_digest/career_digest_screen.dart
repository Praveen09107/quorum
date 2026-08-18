// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.
//
// Three distinct real UI states, matching the three distinct real data
// states: content, "still researching" (the honest 404 case), and
// "researched, found nothing substantial" (the honest empty-success
// case). No shared generic empty-state widget standing in for two
// different real meanings.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/career_digest/career_digest_logic.dart';

class CareerDigestScreen extends StatelessWidget {
  final CompanyDigestData? digest;
  final bool notYetAvailable;

  const CareerDigestScreen({
    super.key,
    required this.digest,
    required this.notYetAvailable,
  });

  @override
  Widget build(BuildContext context) {
    if (notYetAvailable) {
      return const _StillResearchingState();
    }

    final realDigest = digest;
    if (realDigest == null) {
      // Neither state was signaled -- a genuine caller error, not a
      // state this screen invents a message for.
      return const SizedBox.shrink();
    }

    if (hasNoRealContent(realDigest)) {
      return _NothingSubstantialState(company: realDigest.company);
    }

    return _DigestContentState(digest: realDigest);
  }
}

class _StillResearchingState extends StatelessWidget {
  const _StillResearchingState();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Padding(
        padding: EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.hourglass_top),
            SizedBox(height: 8),
            Text('Still researching this company — check back soon.'),
          ],
        ),
      ),
    );
  }
}

class _NothingSubstantialState extends StatelessWidget {
  final String company;

  const _NothingSubstantialState({required this.company});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Text('No notable findings for $company yet.'),
      ),
    );
  }
}

class _DigestContentState extends StatelessWidget {
  final CompanyDigestData digest;

  const _DigestContentState({required this.digest});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(digest.company, style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 8),
        Text(formatSourceCount(digest.sourceCount), style: Theme.of(context).textTheme.bodySmall),
        const SizedBox(height: 16),
        for (final point in digest.summaryPoints)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Text('• $point'),
          ),
      ],
    );
  }
}
