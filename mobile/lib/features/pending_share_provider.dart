// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against `flutter_riverpod` ^2.5.1's
// documented API; `flutter analyze` on a real machine is the actual
// verification.
//
// Deliberately minimal -- a single StateProvider, not a new screen. The
// honest, bounded scope for this session: real classification logic
// already lives in `share_intent_logic.dart`; this file's only job is
// bridging that real, extracted logic to real app state so a widget
// elsewhere in the tree (a bounded SnackBar reaction in `main_shell
// .dart`) can react to a real shared item without the handler and the
// UI needing a direct reference to each other.

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:quorum_mobile/features/share_intent_logic.dart';

/// Holds the most recently classified shared item, if any. Set by
/// `ShareIntentHandler.onSharedContent`; read (and cleared, once shown)
/// by whatever real widget reacts to it.
final pendingShareProvider = StateProvider<SharedContentDraft?>((ref) => null);
