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
// A real navigation link added: You -> Memory Transparency, an
// account-level concern genuinely related to account actions, the same
// reasoning discipline as Trust -> Trust Digest. Deferred, injected
// fetch, same pattern as every other real/external boundary.
//
// Out of scope, deliberately: any account profile display (name, email)
// -- no GET /profile-equivalent endpoint exists, and inventing a display
// for data with no real source would be fabrication.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/memory_transparency/memory_transparency_logic.dart';
import 'package:quorum_mobile/features/memory_transparency/memory_transparency_screen.dart';
import 'package:quorum_mobile/features/you/you_logic.dart';

class YouScreen extends StatefulWidget {
  final Future<DeletionResultData> Function() onConfirmDelete;
  final Future<List<MemoryData>> Function()? onOpenMemories;

  const YouScreen({super.key, required this.onConfirmDelete, this.onOpenMemories});

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
          if (widget.onOpenMemories != null) ...[
            ListTile(
              leading: const Icon(Icons.memory_outlined),
              title: const Text('Manage your memories'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => _MemoriesLoader(fetch: widget.onOpenMemories!)),
              ),
            ),
            const Divider(height: 32),
          ],
          const Text('This permanently deletes your account and all associated data. This cannot be undone.'),
          const SizedBox(height: 16),
          const Text('Type $requiredDeletionConfirmationText to confirm.'),
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

class _MemoriesLoader extends StatelessWidget {
  final Future<List<MemoryData>> Function() fetch;

  const _MemoriesLoader({required this.fetch});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Your memories')),
      body: FutureBuilder<List<MemoryData>>(
        future: fetch(),
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text("Couldn't load your memories: ${snapshot.error}"));
          }
          return MemoryTransparencyScreen(memories: snapshot.data!);
        },
      ),
    );
  }
}
