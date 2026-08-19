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
//
// Batch 10 Phase 4: a real "More" section added below Memory
// Transparency -- Career Pipeline, Finance, Waiting On, and Search, the
// four real, tested screens with no single obviously "closely related"
// existing zone to drill through from (unlike the Gate reveal and the
// negotiation screen, which drill through from Today, or Company
// Digest, which drills through from Career Pipeline itself). Extends
// this tab's own already-established real pattern (it already hosts
// Memory Transparency, itself a domain-adjacent concern, not literally
// "account settings") rather than inventing a new, separate "More" menu
// pattern this codebase has never used anywhere else.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/career/career_pipeline_logic.dart';
import 'package:quorum_mobile/features/career/career_pipeline_screen.dart';
import 'package:quorum_mobile/features/career_digest/career_digest_logic.dart';
import 'package:quorum_mobile/features/career_digest/career_digest_screen.dart';
import 'package:quorum_mobile/features/finance/finance_logic.dart';
import 'package:quorum_mobile/features/finance/finance_screen.dart';
import 'package:quorum_mobile/features/memory_transparency/memory_transparency_logic.dart';
import 'package:quorum_mobile/features/memory_transparency/memory_transparency_screen.dart';
import 'package:quorum_mobile/features/search/search_logic.dart';
import 'package:quorum_mobile/features/search/search_screen.dart';
import 'package:quorum_mobile/features/waiting_on/waiting_on_logic.dart';
import 'package:quorum_mobile/features/waiting_on/waiting_on_screen.dart';
import 'package:quorum_mobile/features/you/you_logic.dart';

class YouScreen extends StatefulWidget {
  final Future<DeletionResultData> Function() onConfirmDelete;
  final Future<List<MemoryData>> Function()? onOpenMemories;
  final Future<List<CareerApplication>> Function()? fetchCareerApplications;
  final Future<CompanyDigestData> Function(String applicationId)? fetchCareerDigest;
  final Future<List<DetectedSubscriptionData>> Function()? fetchFinance;
  final Future<List<WaitingOnItem>> Function()? fetchWaitingOn;
  final Future<List<SearchResultItem>> Function(String query)? fetchSearch;

  const YouScreen({
    super.key,
    required this.onConfirmDelete,
    this.onOpenMemories,
    this.fetchCareerApplications,
    this.fetchCareerDigest,
    this.fetchFinance,
    this.fetchWaitingOn,
    this.fetchSearch,
  });

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

    // A real, deliberate scrollable, added Batch 10 Phase 4: the real
    // content here grew past what a fixed-height Column safely fits --
    // confirmed directly by a real RenderFlex overflow this session's
    // own new navigation tests caught, not assumed defensively. Same
    // reasoning `today_screen.dart`'s own header already documents for
    // its three zones: one shared outer scrollable, not an unbounded
    // Column with nothing to absorb real content taller than the
    // screen.
    return SingleChildScrollView(
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
          if (widget.fetchCareerApplications != null) ...[
            ListTile(
              leading: const Icon(Icons.work_outline),
              title: const Text('Career pipeline'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => _CareerPipelineLoader(
                    fetch: widget.fetchCareerApplications!,
                    fetchDigest: widget.fetchCareerDigest,
                  ),
                ),
              ),
            ),
          ],
          if (widget.fetchFinance != null) ...[
            ListTile(
              leading: const Icon(Icons.payments_outlined),
              title: const Text('Subscriptions'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => _FinanceLoader(fetch: widget.fetchFinance!)),
              ),
            ),
          ],
          if (widget.fetchWaitingOn != null) ...[
            ListTile(
              leading: const Icon(Icons.hourglass_empty),
              title: const Text('Waiting on'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => _WaitingOnLoader(fetch: widget.fetchWaitingOn!)),
              ),
            ),
          ],
          if (widget.fetchSearch != null) ...[
            ListTile(
              leading: const Icon(Icons.search),
              title: const Text('Search'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => _SearchHost(fetch: widget.fetchSearch!)),
              ),
            ),
          ],
          if (widget.fetchCareerApplications != null ||
              widget.fetchFinance != null ||
              widget.fetchWaitingOn != null ||
              widget.fetchSearch != null)
            const Divider(height: 32),
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

class _CareerPipelineLoader extends StatelessWidget {
  final Future<List<CareerApplication>> Function() fetch;
  final Future<CompanyDigestData> Function(String applicationId)? fetchDigest;

  const _CareerPipelineLoader({required this.fetch, this.fetchDigest});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Career pipeline')),
      body: FutureBuilder<List<CareerApplication>>(
        future: fetch(),
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text("Couldn't load your career pipeline: ${snapshot.error}"));
          }
          final digest = fetchDigest;
          return CareerPipelineScreen(
            applications: snapshot.data!,
            onTapApplication: digest == null
                ? null
                : (application) => Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => _CareerDigestLoader(
                          fetch: () => digest(application.applicationId),
                        ),
                      ),
                    ),
          );
        },
      ),
    );
  }
}

/// The real, three-state distinction (`DEC-084`) preserved here too:
/// `DigestNotYetAvailableException` maps to the honest "still
/// researching" state, never silently treated as a generic error.
class _CareerDigestLoader extends StatelessWidget {
  final Future<CompanyDigestData> Function() fetch;

  const _CareerDigestLoader({required this.fetch});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Company research')),
      body: FutureBuilder<CompanyDigestData>(
        future: fetch(),
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.error is DigestNotYetAvailableException) {
            return const CareerDigestScreen(digest: null, notYetAvailable: true);
          }
          if (snapshot.hasError) {
            return Center(child: Text("Couldn't load this company's digest: ${snapshot.error}"));
          }
          return CareerDigestScreen(digest: snapshot.data, notYetAvailable: false);
        },
      ),
    );
  }
}

class _FinanceLoader extends StatelessWidget {
  final Future<List<DetectedSubscriptionData>> Function() fetch;

  const _FinanceLoader({required this.fetch});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Subscriptions')),
      body: FutureBuilder<List<DetectedSubscriptionData>>(
        future: fetch(),
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text("Couldn't load your subscriptions: ${snapshot.error}"));
          }
          return FinanceScreen(subscriptions: snapshot.data!);
        },
      ),
    );
  }
}

class _WaitingOnLoader extends StatelessWidget {
  final Future<List<WaitingOnItem>> Function() fetch;

  const _WaitingOnLoader({required this.fetch});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Waiting on')),
      body: FutureBuilder<List<WaitingOnItem>>(
        future: fetch(),
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text("Couldn't load what you're waiting on: ${snapshot.error}"));
          }
          return WaitingOnScreen(items: snapshot.data!, now: DateTime.now());
        },
      ),
    );
  }
}

/// A real, necessary host `SearchScreen` itself doesn't provide --
/// `SearchScreen` is deliberately a pure results display (its own file
/// header: results arrive already-sorted, server-side), with no query
/// input of its own. This is the real query-input surface, submitting
/// to the injected `fetch` and showing results once resolved.
class _SearchHost extends StatefulWidget {
  final Future<List<SearchResultItem>> Function(String query) fetch;

  const _SearchHost({required this.fetch});

  @override
  State<_SearchHost> createState() => _SearchHostState();
}

class _SearchHostState extends State<_SearchHost> {
  final _controller = TextEditingController();
  Future<List<SearchResultItem>>? _results;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _submit() {
    final query = _controller.text.trim();
    if (query.isEmpty) return;
    // A real bug this session's own new test caught: an arrow-bodied
    // `setState(() => _results = widget.fetch(query))` returns the
    // ASSIGNMENT'S value -- a real Future -- as the callback's return
    // value, which `setState()` explicitly rejects ("callback argument
    // returned a Future"). A statement body, not an expression body,
    // fixes it: the assignment still happens, but the callback itself
    // returns void.
    setState(() {
      _results = widget.fetch(query);
    });
  }

  @override
  Widget build(BuildContext context) {
    final results = _results;
    return Scaffold(
      appBar: AppBar(title: const Text('Search')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              controller: _controller,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                hintText: 'Search emails, tasks, expenses...',
              ),
              textInputAction: TextInputAction.search,
              onSubmitted: (_) => _submit(),
            ),
          ),
          Expanded(
            child: results == null
                ? const Center(child: Text('Search across your real data.'))
                : FutureBuilder<List<SearchResultItem>>(
                    future: results,
                    builder: (context, snapshot) {
                      if (snapshot.connectionState != ConnectionState.done) {
                        return const Center(child: CircularProgressIndicator());
                      }
                      if (snapshot.hasError) {
                        return Center(child: Text("Couldn't search: ${snapshot.error}"));
                      }
                      return SearchScreen(results: snapshot.data!);
                    },
                  ),
          ),
        ],
      ),
    );
  }
}
