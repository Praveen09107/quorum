// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.
//
// Most expensive subscription sorts first -- the most actionable
// ordering for a screen whose real purpose is helping someone decide
// what to cut.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/finance/finance_logic.dart';

class FinanceScreen extends StatelessWidget {
  final List<DetectedSubscriptionData> subscriptions;

  const FinanceScreen({super.key, required this.subscriptions});

  @override
  Widget build(BuildContext context) {
    final sorted = sortByAmountDesc(subscriptions);

    if (sorted.isEmpty) {
      return const Center(child: Text('No recurring subscriptions detected.'));
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: sorted.length,
      itemBuilder: (context, index) {
        final subscription = sorted[index];
        return Card(
          child: ListTile(
            title: Text(subscription.payee),
            subtitle: Text('Every ${formatInterval(subscription.averageIntervalDays)} · ${subscription.occurrences} charges seen'),
            trailing: Text(
              formatCurrency(subscription.averageAmount),
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ),
        );
      },
    );
  }
}
