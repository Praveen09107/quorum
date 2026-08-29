// Phase 7 (`DEC-153`) -- a real, minimal free-text capture screen.
// Matches `you_screen.dart`'s own `_SearchHost` structural convention
// exactly (a real query-input host, submitting to an injected fetch,
// showing the result once resolved) -- the same established pattern,
// not a new one invented for this screen.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/gate_reveal/gate_reveal_screen.dart';
import 'package:quorum_mobile/features/quick_capture/quick_capture_logic.dart';
import 'package:quorum_mobile/theme/quorum_theme.dart';
import 'package:quorum_mobile/theme/spacing.dart';

class QuickCaptureScreen extends StatefulWidget {
  final Future<QuickCaptureResultData> Function(String text) capture;

  const QuickCaptureScreen({super.key, required this.capture});

  @override
  State<QuickCaptureScreen> createState() => _QuickCaptureScreenState();
}

class _QuickCaptureScreenState extends State<QuickCaptureScreen> {
  final _controller = TextEditingController();
  Future<QuickCaptureResultData>? _result;

  // RESOLVED, a real, disclosed CRITICAL-tier review MEDIUM (`DEC-153`
  // M4): this screen's own `Create` button was never disabled while a
  // real request was already in flight -- a real, rapid double-tap
  // (unlike `_SearchHost`'s own identical pattern, which is genuinely
  // safe for a real READ) fired two real, billed extraction calls and
  // could genuinely create two real `tasks` rows from one real user
  // intent. `_isSubmitting` guards both the button and the text field's
  // own `onSubmitted` the same way.
  bool _isSubmitting = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_isSubmitting) return;
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    setState(() {
      _isSubmitting = true;
      _result = widget.capture(text);
    });
    try {
      await _result;
    } catch (_) {
      // The real error itself is already surfaced by the FutureBuilder
      // below -- this catch exists only so `finally` below genuinely
      // always runs, real success or real failure alike.
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final result = _result;
    return Scaffold(
      appBar: AppBar(title: const Text('Quick capture')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(QuorumSpacing.md),
            child: TextField(
              controller: _controller,
              minLines: 2,
              maxLines: 4,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                hintText: "What do you want to get done? e.g. \"Finish the Q3 budget review by next Friday, 2 hours\"",
              ),
              textInputAction: TextInputAction.done,
              enabled: !_isSubmitting,
              onSubmitted: (_) => _submit(),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: QuorumSpacing.md),
            child: SizedBox(
              width: double.infinity,
              child: FilledButton(
                onPressed: _isSubmitting ? null : _submit,
                child: _isSubmitting
                    ? const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Text('Create'),
              ),
            ),
          ),
          const SizedBox(height: QuorumSpacing.md),
          Expanded(
            child: result == null
                ? const Center(child: Text('Real proposals go through the real Gate, just like everything else.'))
                : FutureBuilder<QuickCaptureResultData>(
                    future: result,
                    builder: (context, snapshot) {
                      if (snapshot.connectionState != ConnectionState.done) {
                        return const Center(child: CircularProgressIndicator());
                      }
                      if (snapshot.hasError) {
                        return Center(child: Text('${snapshot.error}'));
                      }
                      return _QuickCaptureResultView(result: snapshot.data!);
                    },
                  ),
          ),
        ],
      ),
    );
  }
}

/// Renders the real outcome banner, then reuses `GateRevealScreen`'s own
/// exact real `Finding`-rendering discipline -- ONE shared scrollable
/// for the whole result (never a `ListView` nested inside another
/// scrollable, the same layout discipline `today_screen.dart`'s own
/// header already establishes for this codebase).
class _QuickCaptureResultView extends StatelessWidget {
  final QuickCaptureResultData result;

  const _QuickCaptureResultView({required this.result});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(QuorumSpacing.md),
      children: [
        // A real, disclosed fix (Phase 8 Session 4, `DEC-158`): this
        // banner previously used a raw `Colors.green` literal for
        // `executed == true` and no color at all otherwise -- the one
        // real status signal in this app that had never been wired to
        // `QuorumStatusColors`. `false` deliberately maps to
        // `needsAttention`, not `critical`: a real Gate `revise`/
        // `reject`/`escalate_to_human` decision here is an honest,
        // informational outcome, not a confirmed failure -- the same
        // uniform treatment this screen's own `describeQuickCaptureOutcome`
        // already gives all three non-executed decisions collectively.
        ListTile(
          leading: QuorumIconBadge(
            icon: result.executed ? Icons.check_circle : Icons.info_outline,
            color: result.executed ? QuorumStatusColors.verified : QuorumStatusColors.needsAttention,
          ),
          title: Text(describeQuickCaptureOutcome(result)),
        ),
        const Divider(height: QuorumSpacing.xl),
        Text('What the Gate checked', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: QuorumSpacing.sm),
        for (final finding in result.findings) FindingRow(finding: finding),
      ],
    );
  }
}
