import 'package:flutter/material.dart';

/// Real, shared motion constants (Phase 8 Session 4, `DEC-158`) -- this
/// app's first real animation of any kind (confirmed by a full grep
/// across `mobile/lib` before writing this file: no `AnimatedContainer`/
/// `AnimatedOpacity`/`AnimationController`/`TweenAnimationBuilder` existed
/// anywhere in this codebase before this session). Two real, deliberately
/// short durations -- matching this project's own stated restraint
/// ("real, small, purposeful animation, not decorative motion for its
/// own sake"), not a general-purpose animation framework.
class QuorumMotion {
  QuorumMotion._();

  /// A genuine STAGED reveal -- Stage B of a Gate verdict, or a
  /// negotiation's real accepted outcome, appearing a deliberate beat
  /// after the content around it, not simultaneously.
  static const Duration reveal = Duration(milliseconds: 350);

  /// A quieter cross-fade for a value that already existed and just
  /// changed (e.g. a real capacity/budget number updating).
  static const Duration transition = Duration(milliseconds: 250);

  /// Real, honored reduced-motion respect -- `Duration.zero` when the
  /// platform's own accessibility setting asks for it (`MediaQuery
  /// .disableAnimations`), matching this project's existing pattern of
  /// never overriding an explicit accessibility signal (the same
  /// discipline `QuorumStatusColors`' own "never color alone" rule
  /// already applies to a different signal). Flutter's implicit
  /// animation widgets (`AnimatedOpacity`, `TweenAnimationBuilder`, ...)
  /// do NOT honor this setting on their own -- resolving every real
  /// duration through this helper is what actually makes that honoring
  /// real, not just a comment claiming it.
  static Duration resolve(BuildContext context, Duration duration) {
    return MediaQuery.of(context).disableAnimations ? Duration.zero : duration;
  }
}
