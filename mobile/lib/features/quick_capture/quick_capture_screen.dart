// Phase 7 (`DEC-153`) -- a real, minimal free-text capture screen.
// Matches `you_screen.dart`'s own `_SearchHost` structural convention
// exactly (a real query-input host, submitting to an injected fetch,
// showing the result once resolved) -- the same established pattern,
// not a new one invented for this screen.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/gate_reveal/gate_reveal_screen.dart';
import 'package:quorum_mobile/features/quick_capture/quick_capture_logic.dart';

class QuickCaptureScreen extends StatefulWidget {
  final Future<QuickCaptureResultData> Function(String text) capture;

  const QuickCaptureScreen({super.key, required this.capture});

  @override
  State<QuickCaptureScreen> createState() => _QuickCaptureScreenState();
}

class _QuickCaptureScreenState extends State<QuickCaptureScreen> {
  final _controller = TextEditingController();
  Future<QuickCaptureResultData>? _result;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _submit() {
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    setState(() {
      _result = widget.capture(text);
    });
  }

  @override
  Widget build(BuildContext context) {
    final result = _result;
    return Scaffold(
      appBar: AppBar(title: const Text('Quick capture')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              controller: _controller,
              minLines: 2,
              maxLines: 4,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                hintText: "What do you want to get done? e.g. \"Finish the Q3 budget review by next Friday, 2 hours\"",
              ),
              textInputAction: TextInputAction.done,
              onSubmitted: (_) => _submit(),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: SizedBox(
              width: double.infinity,
              child: FilledButton(onPressed: _submit, child: const Text('Create')),
            ),
          ),
          const SizedBox(height: 16),
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
      padding: const EdgeInsets.all(16),
      children: [
        ListTile(
          leading: Icon(
            result.executed ? Icons.check_circle : Icons.info_outline,
            color: result.executed ? Colors.green : null,
          ),
          title: Text(describeQuickCaptureOutcome(result)),
        ),
        const Divider(height: 32),
        Text('What the Gate checked', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        for (final finding in result.findings) FindingRow(finding: finding),
      ],
    );
  }
}
