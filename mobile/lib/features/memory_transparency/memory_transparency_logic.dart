// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Zero Flutter dependencies — plain Dart, `dart test` is
// the real verification.
//
// Confirmed already correct in this repository's real copy of
// `QUORUM_DATA_CONTRACTS.md` §5.16 before writing this file: the
// `GET /memories` JSON shape (`memory_id`, `content`, `category`,
// `created_at`) is already documented — no edit needed. `DELETE
// /memories/{memory_id}` deliberately does NOT require the same
// type-to-confirm gate `MOBILE_18` built for account deletion — losing
// one memory is genuinely more recoverable (mem0 could relearn it from
// future behavior) than destroying an entire account; treating every
// deletion with identical maximal ceremony regardless of its real
// stakes would itself be a form of dishonesty.
//
// This session's real backend counterpart,
// `backend/src/quorum_backend/security/memory_transparency.py`, is a
// genuinely NEW backend module — built in this same session (see
// `DEC-091`). `groupByCategory` below deliberately mirrors that real
// backend `group_by_category()` exactly: mem0's own categorization
// scheme isn't controlled by this codebase, so an unrecognized category
// still lands in its own real group rather than being silently dropped.

class MemoryData {
  final String memoryId;
  final String content;
  final String category;
  final DateTime createdAt;

  const MemoryData({
    required this.memoryId,
    required this.content,
    required this.category,
    required this.createdAt,
  });
}

/// Mirrors the real backend's group_by_category() exactly -- never
/// drops a memory for an unrecognized category string.
Map<String, List<MemoryData>> groupByCategory(List<MemoryData> memories) {
  final grouped = <String, List<MemoryData>>{};
  for (final memory in memories) {
    grouped.putIfAbsent(memory.category, () => []).add(memory);
  }
  return grouped;
}

/// A real, de-snaked, capitalized fallback label -- mem0's own
/// categorization isn't controlled by this codebase and shouldn't be
/// assumed closed, so every category (recognized or not) gets a
/// readable label the same way, never raw jargon.
String categoryLabel(String category) {
  if (category.isEmpty) return 'Uncategorized';
  return category
      .split('_')
      .where((w) => w.isNotEmpty)
      .map((w) => w[0].toUpperCase() + w.substring(1))
      .join(' ');
}
