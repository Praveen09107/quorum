// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.
//
// A real, deliberate absence, stated directly like every other one in
// this project (the negotiation screen's missing recommendation logic,
// MOBILE_11's open-vocabulary handling): this widget renders results in
// EXACTLY the order received from the repository, never re-sorting them.
// Search ranking requires scoring the full corpus server-side; the array
// order the backend returns IS the ranking.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/search/search_logic.dart';

class SearchScreen extends StatelessWidget {
  final List<SearchResultItem> results;

  const SearchScreen({super.key, required this.results});

  @override
  Widget build(BuildContext context) {
    if (results.isEmpty) {
      return const Center(child: Text('No results.'));
    }

    // No sort call here, deliberately -- see file header.
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: results.length,
      itemBuilder: (context, index) {
        final item = results[index];
        return ListTile(
          leading: _iconForType(item.itemType),
          title: Text(item.text),
          trailing: Text(labelForItemType(item.itemType)),
        );
      },
    );
  }

  Icon _iconForType(SearchItemType type) {
    switch (type) {
      case SearchItemType.email:
        return const Icon(Icons.email_outlined);
      case SearchItemType.task:
        return const Icon(Icons.check_box_outlined);
      case SearchItemType.expense:
        return const Icon(Icons.payments_outlined);
      case SearchItemType.decision:
        return const Icon(Icons.gavel_outlined);
      case SearchItemType.unknown:
        return const Icon(Icons.help_outline);
    }
  }
}
