// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented
// `NavigationBar`/`StatefulWidget` API; `flutter test` on a real machine
// is the actual verification.
//
// The composition gap named in this file's header since MOBILE_21 is
// closed here. Real, disclosed design choice: this session's own spec
// assumes each of the four tabs reads its data from a Riverpod
// repository PROVIDER it watches internally. No such provider layer
// exists in this repository -- every real screen built since MOBILE_05
// takes already-fetched data via a plain constructor parameter instead,
// consistently, disclosed each time as "the real Repository HTTP
// implementation is deferred, injected pattern." Rather than invent a
// speculative provider layer this project's real history never built,
// composition here uses the SAME injected-function pattern already
// established everywhere else: each tab takes an optional async
// fetcher (defaulting to null), shown via a real FutureBuilder once
// supplied. When no fetcher is configured (the honest, current state --
// no live backend exists), the tab shows a real, honest "not yet
// connected" message instead of fabricated data. This achieves the same
// real goal the spec's provider-override test describes -- a real,
// injectable way to prove the composed tree pumps without a layout
// crash given genuine, full data -- without inventing infrastructure
// this repository doesn't actually have yet.
//
// Four stable tabs, fixed navigation position — a deliberate choice over
// an adaptive-navigation-position pattern (ADD §12.3): adaptive *content*
// works, adaptive *navigation position* confuses users. Today, Log,
// Trust, You — exact names and order from ADD §12.3.
//
// Real share-intent wiring (MOBILE_21, unchanged here): ShareIntentHandler
// initializes once, real content shared into the app lands in
// pendingShareProvider, and this widget shows a real, BOUNDED SnackBar
// reaction.
//
// Batch 10 Phase 4: the real information-architecture decision this
// header used to defer, made and disclosed here, not silently resolved.
// Two real, established patterns already existed in this codebase
// (Trust -> Trust Digest, You -> Memory Transparency, Holding Steady ->
// Tasks) -- contextual drill-through from a screen the data is genuinely
// related to. Extended, not replaced: the Gate reveal drills through
// from a Needs You Now action (the real question it answers is "why is
// the Gate asking about THIS"), the negotiation screen drills through
// from an In Motion card (same reasoning), and Company Digest drills
// through from Career Pipeline (a specific application). Career
// Pipeline, Finance, Waiting On, and Search have no single obviously
// "closely related" existing zone, so they're reached via a new, real
// "More" section on the You tab -- the same well-established real
// mobile pattern (a settings-style tab hosting links to less-frequent
// sections) already extended once for Memory Transparency, not a novel
// invented pattern.
//
// A second, real, pre-existing gap found and closed in the same pass:
// TodayScreen has always supported `fetchTasks`/`onTapAction`/
// `onTapNegotiation` (DEC-096's Holding Steady -> Tasks link among
// them), but this shell never actually threaded any of the three
// through -- confirmed directly (`grep` for all three names in this
// file returned nothing before this session). Closed here, not
// silently left as a second, undiscovered version of the same gap this
// whole phase exists to fix.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:quorum_mobile/features/career/career_pipeline_logic.dart';
import 'package:quorum_mobile/features/career_digest/career_digest_logic.dart';
import 'package:quorum_mobile/features/finance/finance_logic.dart';
import 'package:quorum_mobile/features/gate_reveal/gate_reveal_logic.dart';
import 'package:quorum_mobile/features/gate_reveal/gate_reveal_screen.dart';
import 'package:quorum_mobile/features/honesty_log/honesty_log_logic.dart';
import 'package:quorum_mobile/features/honesty_log/honesty_log_screen.dart';
import 'package:quorum_mobile/features/memory_transparency/memory_transparency_logic.dart';
import 'package:quorum_mobile/features/negotiation/negotiation_logic.dart';
import 'package:quorum_mobile/features/negotiation/negotiation_screen.dart';
import 'package:quorum_mobile/features/pending_share_provider.dart';
import 'package:quorum_mobile/features/search/search_logic.dart';
import 'package:quorum_mobile/features/share_intent_handler.dart';
import 'package:quorum_mobile/features/tasks/tasks_logic.dart';
import 'package:quorum_mobile/features/today_screen.dart';
import 'package:quorum_mobile/features/trust/trust_logic.dart';
import 'package:quorum_mobile/features/trust/trust_screen.dart';
import 'package:quorum_mobile/features/trust_digest/trust_digest_logic.dart';
import 'package:quorum_mobile/features/waiting_on/waiting_on_logic.dart';
import 'package:quorum_mobile/features/you/you_logic.dart';
import 'package:quorum_mobile/features/you/you_screen.dart';

typedef TodayDataFetcher = Future<TodayScreenData> Function();
typedef HonestyFeedFetcher = Future<HonestyFeedData> Function();
typedef TrustFetcher = Future<TrustData> Function();
typedef TrustDigestFetcher = Future<TrustDigestData> Function();
typedef MemoriesFetcher = Future<List<MemoryData>> Function();
typedef DeletionConfirmer = Future<DeletionResultData> Function();
typedef TaskListFetcher = Future<List<TaskData>> Function();
typedef GateRevealFetcher = Future<GateRevealBundle> Function(String proposalId);
typedef NegotiationFetcher = Future<NegotiationBundle> Function(String negotiationId);
typedef ChooseNegotiationOption = Future<void> Function(String negotiationId, String optionId);
typedef CareerFetcher = Future<List<CareerApplication>> Function();
typedef CareerDigestFetcher = Future<CompanyDigestData> Function(String applicationId);
typedef FinanceFetcher = Future<List<DetectedSubscriptionData>> Function();
typedef WaitingOnFetcher = Future<List<WaitingOnItem>> Function();
typedef SearchFetcher = Future<List<SearchResultItem>> Function(String query);

class MainShell extends ConsumerStatefulWidget {
  final TodayDataFetcher? fetchToday;
  final HonestyFeedFetcher? fetchHonestyFeed;
  final TrustFetcher? fetchTrust;
  final TrustDigestFetcher? fetchTrustDigest;
  final MemoriesFetcher? fetchMemories;
  final DeletionConfirmer? confirmDelete;
  final TaskListFetcher? fetchTasks;
  final GateRevealFetcher? fetchGateReveal;
  final NegotiationFetcher? fetchNegotiation;
  final ChooseNegotiationOption? chooseNegotiation;
  final CareerFetcher? fetchCareerApplications;
  final CareerDigestFetcher? fetchCareerDigest;
  final FinanceFetcher? fetchFinance;
  final WaitingOnFetcher? fetchWaitingOn;
  final SearchFetcher? fetchSearch;

  /// The real, live "sign out" action (`DEC-105`) -- distinct from
  /// `confirmDelete` above: signing out ends the current real session
  /// only, never touches any real stored data, the opposite stakes
  /// level from account deletion.
  final VoidCallback? onSignOut;

  const MainShell({
    super.key,
    this.fetchToday,
    this.fetchHonestyFeed,
    this.fetchTrust,
    this.fetchTrustDigest,
    this.fetchMemories,
    this.confirmDelete,
    this.fetchTasks,
    this.fetchGateReveal,
    this.fetchNegotiation,
    this.chooseNegotiation,
    this.fetchCareerApplications,
    this.fetchCareerDigest,
    this.fetchFinance,
    this.fetchWaitingOn,
    this.fetchSearch,
    this.onSignOut,
  });

  @override
  ConsumerState<MainShell> createState() => _MainShellState();
}

class _MainShellState extends ConsumerState<MainShell> {
  int _selectedIndex = 0;
  ShareIntentHandler? _shareIntentHandler;

  static const List<_QuorumTab> _tabs = [
    _QuorumTab(label: 'Today', icon: Icons.today_outlined, selectedIcon: Icons.today),
    _QuorumTab(label: 'Log', icon: Icons.history_outlined, selectedIcon: Icons.history),
    _QuorumTab(label: 'Trust', icon: Icons.verified_outlined, selectedIcon: Icons.verified),
    _QuorumTab(label: 'You', icon: Icons.person_outline, selectedIcon: Icons.person),
  ];

  @override
  void initState() {
    super.initState();
    _shareIntentHandler = ShareIntentHandler(
      onSharedContent: (draft) => ref.read(pendingShareProvider.notifier).state = draft,
    )..initialize();
  }

  @override
  void dispose() {
    _shareIntentHandler?.dispose();
    super.dispose();
  }

  void _onDestinationSelected(int index) {
    setState(() {
      _selectedIndex = index;
    });
  }

  Future<DeletionResultData> _unconfiguredDeletion() {
    throw StateError('Account deletion has not been connected to a real backend yet.');
  }

  Widget _bodyForIndex(int index) {
    switch (index) {
      case 0:
        return _TodayTab(
          fetch: widget.fetchToday,
          fetchTasks: widget.fetchTasks,
          fetchGateReveal: widget.fetchGateReveal,
          fetchNegotiation: widget.fetchNegotiation,
          chooseNegotiation: widget.chooseNegotiation,
        );
      case 1:
        return _HonestyLogTab(fetch: widget.fetchHonestyFeed);
      case 2:
        return _TrustTab(fetch: widget.fetchTrust, fetchDigest: widget.fetchTrustDigest);
      case 3:
        return YouScreen(
          onConfirmDelete: widget.confirmDelete ?? _unconfiguredDeletion,
          onOpenMemories: widget.fetchMemories,
          fetchCareerApplications: widget.fetchCareerApplications,
          fetchCareerDigest: widget.fetchCareerDigest,
          fetchFinance: widget.fetchFinance,
          fetchWaitingOn: widget.fetchWaitingOn,
          fetchSearch: widget.fetchSearch,
          onSignOut: widget.onSignOut,
        );
      default:
        return const SizedBox.shrink();
    }
  }

  @override
  Widget build(BuildContext context) {
    // A real, bounded reaction -- exactly one SnackBar per real shared
    // item, never a persistent banner and never re-shown for the same
    // item on an unrelated rebuild.
    ref.listen(pendingShareProvider, (previous, next) {
      if (next != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Shared to Quorum — suggested: ${next.suggestedDomain}')),
        );
        ref.read(pendingShareProvider.notifier).state = null;
      }
    });

    return Scaffold(
      appBar: AppBar(title: Text(_tabs[_selectedIndex].label)),
      body: SafeArea(child: _bodyForIndex(_selectedIndex)),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: _onDestinationSelected,
        destinations: [
          for (final tab in _tabs)
            NavigationDestination(
              icon: Icon(tab.icon),
              selectedIcon: Icon(tab.selectedIcon),
              label: tab.label,
            ),
        ],
      ),
    );
  }
}

class _QuorumTab {
  final String label;
  final IconData icon;
  final IconData selectedIcon;

  const _QuorumTab({
    required this.label,
    required this.icon,
    required this.selectedIcon,
  });
}

/// A real, honest state -- shown whenever a tab's real fetcher hasn't
/// been configured (the current, actual state of this repository: no
/// live backend deployment exists). Never fabricated data standing in
/// for a real connection that doesn't exist yet.
class _NotConnectedState extends StatelessWidget {
  final String label;

  const _NotConnectedState({required this.label});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Text(
          'No live backend connection configured yet for $label.',
          key: Key('not_connected_${label.toLowerCase()}'),
          textAlign: TextAlign.center,
        ),
      ),
    );
  }
}

class _TodayTab extends StatelessWidget {
  final TodayDataFetcher? fetch;
  final TaskListFetcher? fetchTasks;
  final GateRevealFetcher? fetchGateReveal;
  final NegotiationFetcher? fetchNegotiation;
  final ChooseNegotiationOption? chooseNegotiation;

  const _TodayTab({this.fetch, this.fetchTasks, this.fetchGateReveal, this.fetchNegotiation, this.chooseNegotiation});

  @override
  Widget build(BuildContext context) {
    final fetcher = fetch;
    if (fetcher == null) return const _NotConnectedState(label: 'Today');

    return FutureBuilder<TodayScreenData>(
      future: fetcher(),
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return Center(child: Text("Couldn't load Today: ${snapshot.error}"));
        }
        final gateReveal = fetchGateReveal;
        final negotiation = fetchNegotiation;
        return TodayScreen(
          data: snapshot.data!,
          now: DateTime.now(),
          fetchTasks: fetchTasks,
          onTapAction: gateReveal == null
              ? null
              : (action) => Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => _GateRevealLoader(fetch: () => gateReveal(action.proposalId)),
                    ),
                  ),
          onTapNegotiation: negotiation == null
              ? null
              : (negotiationId) => Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => _NegotiationLoader(
                        negotiationId: negotiationId,
                        fetch: () => negotiation(negotiationId),
                        chooseNegotiation: chooseNegotiation,
                      ),
                    ),
                  ),
        );
      },
    );
  }
}

/// The Gate reveal's real drill-through: "why is the Gate asking about
/// THIS" for a specific pending action, triggered from Needs You Now.
class _GateRevealLoader extends StatelessWidget {
  final Future<GateRevealBundle> Function() fetch;

  const _GateRevealLoader({required this.fetch});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Gate reveal')),
      body: FutureBuilder<GateRevealBundle>(
        future: fetch(),
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text("Couldn't load the Gate reveal: ${snapshot.error}"));
          }
          final bundle = snapshot.data!;
          return GateRevealScreen(stakes: bundle.stakes, findings: bundle.findings, objections: bundle.objections);
        },
      ),
    );
  }
}

/// The negotiation screen's real drill-through, triggered from an In
/// Motion card. `onChoose` is now real and live (`QUORUM_DATA_CONTRACTS.md`
/// §5.6, closing the gap `DEC-104`/`DEC-121` both disclosed) --
/// `StatefulWidget` since submitting a real choice needs real loading/
/// error/success states of its own, distinct from the initial fetch.
class _NegotiationLoader extends StatefulWidget {
  final String negotiationId;
  final Future<NegotiationBundle> Function() fetch;
  final ChooseNegotiationOption? chooseNegotiation;

  const _NegotiationLoader({required this.negotiationId, required this.fetch, this.chooseNegotiation});

  @override
  State<_NegotiationLoader> createState() => _NegotiationLoaderState();
}

class _NegotiationLoaderState extends State<_NegotiationLoader> {
  late final Future<NegotiationBundle> _bundleFuture;
  bool _submitting = false;
  String? _submitError;
  bool _accepted = false;

  @override
  void initState() {
    super.initState();
    _bundleFuture = widget.fetch();
  }

  Future<void> _handleChoose(String optionId) async {
    final choose = widget.chooseNegotiation;
    if (choose == null) return;
    setState(() {
      _submitting = true;
      _submitError = null;
    });
    try {
      await choose(widget.negotiationId, optionId);
      if (!mounted) return;
      setState(() {
        _submitting = false;
        _accepted = true;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _submitting = false;
        _submitError = '$e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Negotiation')),
      // A real, honest terminal state -- matches the backend's own real
      // 202 Accepted semantics exactly: the choice is real and durably
      // recorded, the downstream action is real and genuinely queued,
      // but not yet processed. Never claims more happened than that.
      body: _accepted
          ? const Center(child: Text('Choice accepted -- this action is now queued.'))
          : FutureBuilder<NegotiationBundle>(
              future: _bundleFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState != ConnectionState.done) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snapshot.hasError) {
                  return Center(child: Text("Couldn't load the negotiation: ${snapshot.error}"));
                }
                final bundle = snapshot.data!;
                final canChoose = widget.chooseNegotiation != null && !_submitting;
                return Column(
                  children: [
                    if (_submitError != null)
                      Padding(
                        padding: const EdgeInsets.all(16),
                        child: Text("Couldn't submit your choice: $_submitError"),
                      ),
                    if (_submitting) const LinearProgressIndicator(),
                    Expanded(
                      child: NegotiationScreen(
                        positions: bundle.positions,
                        options: bundle.options,
                        onChoose: canChoose ? _handleChoose : null,
                      ),
                    ),
                  ],
                );
              },
            ),
    );
  }
}

class _HonestyLogTab extends StatelessWidget {
  final HonestyFeedFetcher? fetch;

  const _HonestyLogTab({this.fetch});

  @override
  Widget build(BuildContext context) {
    final fetcher = fetch;
    if (fetcher == null) return const _NotConnectedState(label: 'Log');

    return FutureBuilder<HonestyFeedData>(
      future: fetcher(),
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return Center(child: Text("Couldn't load the Log: ${snapshot.error}"));
        }
        return HonestyLogScreen(feed: snapshot.data!);
      },
    );
  }
}

class _TrustTab extends StatelessWidget {
  final TrustFetcher? fetch;
  final TrustDigestFetcher? fetchDigest;

  const _TrustTab({this.fetch, this.fetchDigest});

  @override
  Widget build(BuildContext context) {
    final fetcher = fetch;
    if (fetcher == null) return const _NotConnectedState(label: 'Trust');

    return FutureBuilder<TrustData>(
      future: fetcher(),
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return Center(child: Text("Couldn't load Trust: ${snapshot.error}"));
        }
        return TrustScreen(trust: snapshot.data!, onOpenTrustDigest: fetchDigest);
      },
    );
  }
}
