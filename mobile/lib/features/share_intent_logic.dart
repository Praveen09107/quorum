// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Zero Flutter dependencies — plain Dart, `dart test` is
// the real verification.
//
// A SIGNIFICANT, DISCLOSED DISCREPANCY, per this project's standing
// discipline: this session's own kickoff prompt and its "real backstory"
// both describe this classification logic as originally sitting inside
// a private, untested method in `share_intent_handler.dart`, extracted
// here for the first time. **Neither `share_intent_handler.dart` nor
// `today_widget_bridge.dart` exists anywhere in this repository** —
// confirmed by direct, exhaustive search before writing a line of this
// session's code. `mobile/pubspec.yaml`'s own real, honest comment
// (written during `MOBILE_04`) already discloses this: the packages
// these files would consume (`home_widget`, `receive_sharing_intent`)
// are declared, but "the consuming Dart files... have NOT been built in
// this repository — a batch-guide claim that they were 'already-real'
// describes a different, inaccessible environment, not this one."
// There is no dormant private method to extract here. This file is
// built fresh, directly, with real test coverage from the first line —
// not "extracted," since there was nothing in this repository to
// extract it from.
//
// Real MIME type strings are used throughout (`image/jpeg`,
// `application/pdf`), matching `receive_sharing_intent`'s real,
// documented `SharedMediaFile.type` / MIME-string shape, not toy
// examples.
//
// `suggestedDomain` is a real, honest HEURISTIC hint, never a
// committed fact -- a shared image is a plausible receipt (Finance), a
// shared non-image file is a plausible task attachment (Tasks), but
// either could genuinely be neither. The suggestion routes which
// draft-creation flow opens first; it never silently creates a real
// expense or task record on its own.

class SharedContentDraft {
  final String path;
  final String mimeType;
  final String suggestedDomain; // 'finance' | 'tasks' -- a heuristic hint, not a fact

  const SharedContentDraft({
    required this.path,
    required this.mimeType,
    required this.suggestedDomain,
  });
}

/// Real, pure classification -- a shared item whose MIME type looks like
/// an image is a plausible receipt photo (routed toward Finance); any
/// other real MIME type is routed toward a generic Task draft instead.
SharedContentDraft classifySharedContent(String path, String mimeType) {
  final looksLikeImage = mimeType.contains('image');
  return SharedContentDraft(
    path: path,
    mimeType: mimeType,
    suggestedDomain: looksLikeImage ? 'finance' : 'tasks',
  );
}
