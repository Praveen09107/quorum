// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this
// file was written. Zero Flutter dependencies (same as the file under
// test) — plain `package:test`, `dart test` is the real verification.
//
// These tests deliberately mirror `backend/tests/test_memory_
// transparency.py`'s exact scenarios — proving both sides of the
// boundary agree, not just that each independently looks reasonable.

import 'package:test/test.dart';

import 'package:quorum_mobile/features/memory_transparency/memory_transparency_logic.dart';

MemoryData _memory(String id, String category) =>
    MemoryData(memoryId: id, content: 'x', category: category, createdAt: DateTime(2026, 7, 1));

void main() {
  group('groupByCategory', () {
    test('groups real memories correctly by category', () {
      final grouped = groupByCategory([
        _memory('1', 'preference'),
        _memory('2', 'preference'),
        _memory('3', 'fact'),
      ]);

      expect(grouped['preference']!.map((m) => m.memoryId).toList(), ['1', '2']);
      expect(grouped['fact']!.map((m) => m.memoryId).toList(), ['3']);
    });

    test('never drops a memory for a genuinely unrecognized category', () {
      final grouped = groupByCategory([_memory('1', 'preference'), _memory('2', 'a_genuinely_new_category')]);
      expect(grouped.containsKey('a_genuinely_new_category'), isTrue);
      expect(grouped['a_genuinely_new_category']!.length, 1);
    });

    test('THE REAL, MOST IMPORTANT PROOF: every memory is accounted for across all groups -- none lost', () {
      final memories = [_memory('1', 'preference'), _memory('2', 'a_genuinely_new_category')];
      final grouped = groupByCategory(memories);
      final totalGrouped = grouped.values.fold<int>(0, (sum, list) => sum + list.length);
      expect(totalGrouped, memories.length);
    });

    test('an empty memory list returns a genuinely empty map, not a crash', () {
      expect(groupByCategory(const []), isEmpty);
    });

    test('does not mutate the input list', () {
      final a = _memory('1', 'preference');
      final original = [a];

      groupByCategory(original);

      expect(original.length, 1);
      expect(original.first.memoryId, '1');
    });

    test('a single category with multiple memories preserves real insertion order', () {
      final grouped = groupByCategory([_memory('1', 'preference'), _memory('2', 'preference'), _memory('3', 'preference')]);
      expect(grouped['preference']!.map((m) => m.memoryId).toList(), ['1', '2', '3']);
    });
  });

  group('categoryLabel', () {
    test('a multi-word category de-snakes and capitalizes correctly', () {
      expect(categoryLabel('personal_preferences'), 'Personal Preferences');
    });

    test('a single-word category capitalizes correctly', () {
      expect(categoryLabel('preference'), 'Preference');
    });

    test('an empty category string falls back honestly, never a crash', () {
      expect(categoryLabel(''), 'Uncategorized');
    });
  });

  test('MemoryData constructs and reads back correctly', () {
    final memory = _memory('1', 'preference');
    expect(memory.memoryId, '1');
    expect(memory.category, 'preference');
  });
}
