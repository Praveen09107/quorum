// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/waiting_on/waiting_on_logic.dart';

class WaitingOnScreen extends StatelessWidget {
  final List<WaitingOnItem> items;
  final DateTime now;

  const WaitingOnScreen({
    super.key,
    required this.items,
    required this.now,
  });

  @override
  Widget build(BuildContext context) {
    final sorted = sortByStaleness(items);

    if (sorted.isEmpty) {
      return const Center(child: Text('No sent messages are waiting on a reply.'));
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: sorted.length,
      itemBuilder: (context, index) {
        final item = sorted[index];
        final days = daysSince(item.sentAt, now);
        return Card(
          child: ListTile(
            leading: const Icon(Icons.hourglass_empty),
            title: Text(item.subject),
            subtitle: Text('To ${item.recipient}'),
            trailing: Text(formatStaleness(days)),
          ),
        );
      },
    );
  }
}
