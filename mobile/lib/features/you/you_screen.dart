// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.
//
// A real type-to-confirm gate: the delete button's onPressed is
// structurally null, not just visually dimmed, until the exact literal
// string "DELETE" is typed. Once deletion succeeds, this screen shows
// the real, backend-reported DeletionResult counts -- never a generic
// "your account has been deleted" message.
//
// Out of scope, deliberately: any account profile display (name, email)
// -- no GET /profile-equivalent endpoint exists, and inventing a display
// for data with no real source would be fabrication.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/you/you_logic.dart';

class YouScreen extends StatefulWidget {
  final Future<DeletionResultData> Function() onConfirmDelete;

  const YouScreen({super.key, required this.onConfirmDelete});

  @override
  State<YouScreen> createState() => _YouScreenState();
}

class _YouScreenState extends State<YouScreen> {
  final _controller = TextEditingController();
  DeletionResultData? _result;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final result = _result;
    if (result != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(formatDeletionSummary(result)),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('This permanently deletes your account and all associated data. This cannot be undone.'),
          const SizedBox(height: 16),
          Text('Type $requiredDeletionConfirmationText to confirm.'),
          const SizedBox(height: 8),
          TextField(
            controller: _controller,
            decoration: const InputDecoration(border: OutlineInputBorder()),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: isValidDeletionConfirmation(_controller.text)
                ? () async {
                    final deletionResult = await widget.onConfirmDelete();
                    if (mounted) setState(() => _result = deletionResult);
                  }
                : null,
            child: const Text('Delete my account'),
          ),
        ],
      ),
    );
  }
}
