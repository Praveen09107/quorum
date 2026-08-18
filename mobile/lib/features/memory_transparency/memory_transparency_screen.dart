// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.
//
// A real, deliberate design decision: deleting one memory uses a plain
// confirmation dialog, never the type-to-confirm gate MOBILE_18 built
// for account deletion -- proportional to its genuinely lower, more
// recoverable stakes.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/memory_transparency/memory_transparency_logic.dart';

class MemoryTransparencyScreen extends StatelessWidget {
  final List<MemoryData> memories;
  final void Function(String memoryId)? onDelete;

  const MemoryTransparencyScreen({super.key, required this.memories, this.onDelete});

  @override
  Widget build(BuildContext context) {
    final grouped = groupByCategory(memories);

    if (grouped.isEmpty) {
      return const Center(child: Text('No memories stored yet.'));
    }

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        for (final category in grouped.keys) _CategorySection(category: category, memories: grouped[category]!, onDelete: onDelete),
      ],
    );
  }
}

class _CategorySection extends StatelessWidget {
  final String category;
  final List<MemoryData> memories;
  final void Function(String memoryId)? onDelete;

  const _CategorySection({required this.category, required this.memories, this.onDelete});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: Text(categoryLabel(category), style: Theme.of(context).textTheme.titleSmall),
        ),
        for (final memory in memories)
          ListTile(
            title: Text(memory.content),
            trailing: onDelete == null
                ? null
                : IconButton(
                    icon: const Icon(Icons.delete_outline),
                    onPressed: () => onDelete!(memory.memoryId),
                  ),
          ),
      ],
    );
  }
}
