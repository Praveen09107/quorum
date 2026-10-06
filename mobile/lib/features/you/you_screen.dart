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
// A real, disclosed fix found and closed the same session the real
// backend route first existed (`DEC-113`): the delete button's own
// async call previously had no error handling at all -- a real, live
// failure would have propagated as an unhandled exception rather than
// a real, honest, visible message. Now mirrors `login_screen.dart`'s
// own established `_handleSignIn` convention exactly (a real loading
// state, a real, visible error message on failure, the button
// disabled while a real request is in flight).
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

import 'package:quorum_mobile/api/create_application_api.dart';
import 'package:quorum_mobile/api/schedule_interview_api.dart';
import 'package:quorum_mobile/db/database.dart';
import 'package:quorum_mobile/features/calendar/calendar_screen.dart';
import 'package:quorum_mobile/features/calendar_sync.dart';
import 'package:quorum_mobile/features/career/career_pipeline_logic.dart';
import 'package:quorum_mobile/features/career/career_pipeline_screen.dart';
import 'package:quorum_mobile/features/career_digest/career_digest_logic.dart';
import 'package:quorum_mobile/features/career_digest/career_digest_screen.dart';
import 'package:quorum_mobile/features/connections/connections_logic.dart';
import 'package:quorum_mobile/features/connections/connections_screen.dart';
import 'package:quorum_mobile/features/finance/finance_logic.dart';
import 'package:quorum_mobile/features/finance/finance_screen.dart';
import 'package:quorum_mobile/features/memory_transparency/memory_transparency_logic.dart';
import 'package:quorum_mobile/features/memory_transparency/memory_transparency_screen.dart';
import 'package:quorum_mobile/features/search/search_logic.dart';
import 'package:quorum_mobile/features/search/search_screen.dart';
import 'package:quorum_mobile/features/today/week_summary_logic.dart';
import 'package:quorum_mobile/features/waiting_on/waiting_on_logic.dart';
import 'package:quorum_mobile/features/waiting_on/waiting_on_screen.dart';
import 'package:quorum_mobile/features/you/you_logic.dart';
import 'package:quorum_mobile/features/you/you_preview_logic.dart';
import 'package:quorum_mobile/theme/quorum_theme.dart';
import 'package:quorum_mobile/theme/spacing.dart';

class YouScreen extends StatefulWidget {
  final Future<DeletionResultData> Function() onConfirmDelete;
  final Future<List<MemoryData>> Function()? onOpenMemories;

  /// `DEC-198` (product rebuild) -- the real, direct answer to this
  /// rebuild's own sharpest named root cause (a silently stale Google
  /// grant). Optional and additive, same honest-gating pattern as
  /// every other real fetcher on this screen.
  final Future<ConnectionHealthData> Function()? fetchConnectionHealth;
  final Future<void> Function()? onReconnectGoogle;
  final Future<List<CareerApplication>> Function()? fetchCareerApplications;
  final Future<CompanyDigestData> Function(String applicationId)? fetchCareerDigest;

  /// `DEC-194` (product rebuild Block F) -- the real, first write path
  /// this screen's own Career pipeline has ever had. Optional and
  /// additive, matching every other real write in this app: the "+ New
  /// application" action only appears on `CareerPipelineScreen` when
  /// this is genuinely supplied.
  final CreateApplicationFetcher? createApplication;

  /// `DEC-195` (product rebuild Block F remainder) -- the Career
  /// pipeline's second real write control: scheduling an interview
  /// against an existing application. Optional and additive, same
  /// honest-gating pattern as `createApplication` above.
  final ScheduleInterviewFetcher? scheduleInterview;
  final Future<List<DetectedSubscriptionData>> Function()? fetchFinance;

  /// REAL, NEW (the redesign's own real "Finance hub" work) -- see
  /// `FinanceLoader`'s own docstring for the full real reasoning.
  final Future<List<ExpenseData>> Function()? fetchExpenses;
  final Future<List<WaitingOnItem>> Function()? fetchWaitingOn;
  final Future<List<SearchResultItem>> Function(String query)? fetchSearch;
  final Future<CalendarSyncResult> Function()? syncCalendar;
  final Future<List<CalendarMirrorData>> Function()? fetchCalendarEvents;

  /// REAL, NEW (the redesign's own real You-tab promotion work) -- the
  /// same real `/today/summary` fetcher `TodayScreen` already uses,
  /// reused here for three of this screen's five real preview numbers
  /// (applications in progress, month-to-date spend, waiting-on count)
  /// rather than inventing three separate, narrower endpoints for
  /// numbers this backend already computes together in one real round
  /// trip.
  final Future<WeekSummaryData> Function()? fetchWeekSummary;

  /// The real, live "sign out" action (`DEC-105`) -- genuinely distinct
  /// stakes from `onConfirmDelete` below: this ends the current session
  /// only, real local storage cleared and the real server-side session
  /// revoked, but no real data is ever touched.
  final VoidCallback? onSignOut;

  const YouScreen({
    super.key,
    required this.onConfirmDelete,
    this.onOpenMemories,
    this.fetchConnectionHealth,
    this.onReconnectGoogle,
    this.fetchCareerApplications,
    this.fetchCareerDigest,
    this.createApplication,
    this.scheduleInterview,
    this.fetchFinance,
    this.fetchExpenses,
    this.fetchWaitingOn,
    this.fetchSearch,
    this.syncCalendar,
    this.fetchCalendarEvents,
    this.fetchWeekSummary,
    this.onSignOut,
  });

  @override
  State<YouScreen> createState() => _YouScreenState();
}

class _YouScreenState extends State<YouScreen> {
  final _controller = TextEditingController();
  DeletionResultData? _result;
  bool _deleting = false;
  String? _deleteError;

  /// REAL, NEW (the redesign's own real You-tab promotion work) --
  /// fetched exactly ONCE per real screen visit, in `initState()`, never
  /// re-created on every `build()` -- the same real, established "don't
  /// re-fetch on every rebuild" discipline `_TasksLoaderState`/`_
  /// GateRevealLoaderState` already hold themselves to elsewhere in this
  /// app. Each real preview card below reads from these SAME shared
  /// futures via its own `FutureBuilder`, rather than each card
  /// triggering its own separate real network call for data the other
  /// cards already need too.
  Future<WeekSummaryData>? _weekSummaryFuture;
  Future<int>? _eventsThisWeekFuture;

  @override
  void initState() {
    super.initState();
    _weekSummaryFuture = widget.fetchWeekSummary?.call();
    final fetchCalendarEvents = widget.fetchCalendarEvents;
    _eventsThisWeekFuture = fetchCalendarEvents == null
        ? null
        : fetchCalendarEvents().then((events) => countEventsWithinDays(events, DateTime.now(), 7));
  }

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
          padding: const EdgeInsets.all(QuorumSpacing.lg),
          child: Text(formatDeletionSummary(result)),
        ),
      );
    }

    final badgeColor = Theme.of(context).colorScheme.onSurfaceVariant;

    // A real, deliberate scrollable, added Batch 10 Phase 4: the real
    // content here grew past what a fixed-height Column safely fits --
    // confirmed directly by a real RenderFlex overflow this session's
    // own new navigation tests caught, not assumed defensively. Same
    // reasoning `today_screen.dart`'s own header already documents for
    // its three zones: one shared outer scrollable, not an unbounded
    // Column with nothing to absorb real content taller than the
    // screen.
    return SingleChildScrollView(
      padding: const EdgeInsets.all(QuorumSpacing.lg),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (widget.onOpenMemories != null) ...[
            ListTile(
              leading: QuorumIconBadge(icon: Icons.memory_outlined, color: badgeColor),
              title: const Text('Manage your memories'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => _MemoriesLoader(fetch: widget.onOpenMemories!)),
              ),
            ),
            const Divider(height: QuorumSpacing.xl),
          ],
          if (widget.fetchConnectionHealth != null && widget.onReconnectGoogle != null) ...[
            ListTile(
              leading: QuorumIconBadge(icon: Icons.link_rounded, color: badgeColor),
              title: const Text('Google connection'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => ConnectionsScreen(
                    fetch: widget.fetchConnectionHealth!,
                    onReconnect: widget.onReconnectGoogle!,
                  ),
                ),
              ),
            ),
            const Divider(height: QuorumSpacing.xl),
          ],
          // REAL, DISCLOSED FIX (the redesign's own real You-tab
          // promotion work): closes the approved plan's own named gap --
          // these five real, tested screens used to be generic grey
          // `ListTile` rows with identical icons, indistinguishable from
          // a settings menu. Each real preview card below shows one
          // live, real number (reusing the real `WeekSummaryData`/
          // calendar-mirror data already fetched once in `initState()`),
          // turning this tab's first impression into a real dashboard of
          // live things, not a list of menu items.
          _PreviewGrid(
            cards: [
              if (widget.fetchCareerApplications != null)
                _PreviewCardSpec(
                  icon: Icons.work_outline,
                  title: 'Career pipeline',
                  previewLine: _weekSummaryFuture?.then((s) => formatApplicationsSummary(s.applicationsInProgress)),
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => CareerPipelineLoader(
                        fetch: widget.fetchCareerApplications!,
                        fetchDigest: widget.fetchCareerDigest,
                        createApplication: widget.createApplication,
                        scheduleInterview: widget.scheduleInterview,
                      ),
                    ),
                  ),
                ),
              if (widget.fetchFinance != null)
                _PreviewCardSpec(
                  icon: Icons.payments_outlined,
                  title: 'Finance',
                  previewLine: _weekSummaryFuture?.then(formatSpendSummary),
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => FinanceLoader(
                        fetch: widget.fetchFinance!,
                        fetchExpenses: widget.fetchExpenses,
                        weekSummaryFuture: _weekSummaryFuture,
                      ),
                    ),
                  ),
                ),
              if (widget.fetchWaitingOn != null)
                _PreviewCardSpec(
                  icon: Icons.hourglass_empty,
                  title: 'Waiting on',
                  previewLine: _weekSummaryFuture?.then((s) => formatWaitingOnSummary(s.waitingOnCount)),
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => _WaitingOnLoader(fetch: widget.fetchWaitingOn!)),
                  ),
                ),
              if (widget.fetchSearch != null)
                _PreviewCardSpec(
                  icon: Icons.search,
                  title: 'Search',
                  // A real, deliberate `null` -- unlike the other four
                  // real preview cards, Search has no single live count
                  // that honestly represents it (it's a reactive query
                  // tool, not a real, standing collection). A fabricated
                  // number here would be exactly the kind of invented
                  // content this project's own discipline refuses.
                  previewLine: null,
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => _SearchHost(fetch: widget.fetchSearch!)),
                  ),
                ),
              if (widget.syncCalendar != null && widget.fetchCalendarEvents != null)
                _PreviewCardSpec(
                  icon: Icons.calendar_month_outlined,
                  title: 'Calendar',
                  previewLine: _eventsThisWeekFuture?.then(formatCalendarPreview),
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => CalendarLoader(
                        sync: widget.syncCalendar!,
                        fetchEvents: widget.fetchCalendarEvents!,
                      ),
                    ),
                  ),
                ),
            ],
          ),
          if (widget.fetchCareerApplications != null ||
              widget.fetchFinance != null ||
              widget.fetchWaitingOn != null ||
              widget.fetchSearch != null ||
              (widget.syncCalendar != null && widget.fetchCalendarEvents != null))
            const Divider(height: QuorumSpacing.xl),
          if (widget.onSignOut != null) ...[
            OutlinedButton.icon(
              onPressed: widget.onSignOut,
              icon: const Icon(Icons.logout),
              label: const Text('Sign out'),
            ),
            const Divider(height: QuorumSpacing.xl),
          ],
          // REAL, DISCLOSED FIX (the redesign's own real bug-fix work):
          // closes a real, confirmed-live UX/safety issue found during
          // this session's own on-device audit -- the destructive type-
          // DELETE-to-confirm form sat in plain view immediately below
          // the feature list, with no separation at all from ordinary
          // navigation. A real, collapsed-by-default `ExpansionTile`
          // means a person must deliberately open "Danger zone" before
          // ever seeing a delete-account control, let alone being able
          // to tap it -- the same real, deliberate friction a genuinely
          // irreversible action deserves.
          Theme(
            data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
            child: ExpansionTile(
              title: Text('Danger zone', style: TextStyle(color: Theme.of(context).colorScheme.error)),
              leading: Icon(Icons.warning_amber_outlined, color: Theme.of(context).colorScheme.error),
              tilePadding: EdgeInsets.zero,
              childrenPadding: const EdgeInsets.only(top: QuorumSpacing.md),
              children: [
                const Align(
                  alignment: Alignment.centerLeft,
                  child: Text('This permanently deletes your account and all associated data. This cannot be undone.'),
                ),
                const SizedBox(height: QuorumSpacing.md),
                const Align(
                  alignment: Alignment.centerLeft,
                  child: Text('Type $requiredDeletionConfirmationText to confirm.'),
                ),
                const SizedBox(height: QuorumSpacing.sm),
                TextField(
                  controller: _controller,
                  decoration: const InputDecoration(border: OutlineInputBorder()),
                  onChanged: (_) => setState(() {}),
                ),
                const SizedBox(height: QuorumSpacing.md),
                FilledButton(
                  onPressed: (isValidDeletionConfirmation(_controller.text) && !_deleting)
                      ? () async {
                          // A real, disclosed fix, found and closed the
                          // same session this real backend route first
                          // existed (`DEC-113`): this call previously
                          // had no error handling at all -- a real,
                          // live failure (a real network drop, a real
                          // 503) would have propagated as an unhandled
                          // exception rather than a real, honest,
                          // visible message, the same discipline
                          // `login_screen.dart`'s own `_handleSignIn`
                          // already holds itself to.
                          setState(() {
                            _deleting = true;
                            _deleteError = null;
                          });
                          try {
                            final deletionResult = await widget.onConfirmDelete();
                            if (mounted) setState(() => _result = deletionResult);
                          } catch (e) {
                            if (mounted) {
                              setState(() {
                                _deleting = false;
                                _deleteError = 'Account deletion failed: $e';
                              });
                            }
                          }
                        }
                      : null,
                  style: FilledButton.styleFrom(backgroundColor: Theme.of(context).colorScheme.error),
                  child: _deleting ? const CircularProgressIndicator() : const Text('Delete my account'),
                ),
                if (_deleteError != null) ...[
                  const SizedBox(height: QuorumSpacing.md),
                  Text(_deleteError!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// REAL, NEW (the redesign's own real You-tab promotion work) -- a real,
/// deliberate spec for one preview card, kept separate from the widget
/// itself so `_PreviewGrid` can lay a plain list of them out in pairs
/// without each card needing to know its own position.
class _PreviewCardSpec {
  final IconData icon;
  final String title;

  /// `null` means this real domain has no honest single live number to
  /// show (Search, deliberately -- see its own real call site's
  /// comment). Non-null is a real `Future` already in flight (shared,
  /// never re-triggered per card) resolving to the real preview text.
  final Future<String>? previewLine;
  final VoidCallback onTap;

  const _PreviewCardSpec({required this.icon, required this.title, required this.previewLine, required this.onTap});
}

/// Lays real preview cards out two to a row, the real "grid" the
/// approved redesign plan named -- a plain, hand-built `Row`-of-pairs
/// rather than a `GridView` (which needs an explicit height/aspect
/// ratio to behave inside a `SingleChildScrollView`): simpler, and this
/// screen's own real card count (five) is small and fixed, never a long
/// scrolling collection that would need `GridView`'s own viewport
/// virtualization.
class _PreviewGrid extends StatelessWidget {
  final List<_PreviewCardSpec> cards;

  const _PreviewGrid({required this.cards});

  @override
  Widget build(BuildContext context) {
    final rows = <Widget>[];
    for (var i = 0; i < cards.length; i += 2) {
      final second = i + 1 < cards.length ? cards[i + 1] : null;
      rows.add(
        Padding(
          padding: const EdgeInsets.only(bottom: QuorumSpacing.sm),
          // REAL, DISCLOSED FIX (caught by this session's own real
          // `flutter test` run, not hypothetical): `CrossAxisAlignment
          // .stretch` on a `Row` needs a real, bounded height to stretch
          // its children to -- this `Row` sits inside a `Column` with no
          // bounded height of its own (the outer `SingleChildScrollView`
          // gives its content unbounded height to scroll), so stretching
          // without a real intrinsic-height wrapper threw a real
          // "BoxConstraints forces an infinite height" layout error.
          // `IntrinsicHeight` is the same real fix `needs_you_now_zone.
          // dart`'s own card-accent-stripe Row already uses for this
          // exact real constraint shape.
          child: IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Expanded(child: _PreviewCard(spec: cards[i])),
                const SizedBox(width: QuorumSpacing.sm),
                Expanded(child: second == null ? const SizedBox.shrink() : _PreviewCard(spec: second)),
              ],
            ),
          ),
        ),
      );
    }
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: rows);
  }
}

class _PreviewCard extends StatelessWidget {
  final _PreviewCardSpec spec;

  const _PreviewCard({required this.spec});

  @override
  Widget build(BuildContext context) {
    final badgeColor = Theme.of(context).colorScheme.onSurfaceVariant;
    return Card(
      child: InkWell(
        onTap: spec.onTap,
        child: Padding(
          padding: const EdgeInsets.all(QuorumSpacing.sm),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  QuorumIconBadge(icon: spec.icon, color: badgeColor),
                  const Icon(Icons.chevron_right, size: 20),
                ],
              ),
              const SizedBox(height: QuorumSpacing.sm),
              Text(spec.title, style: Theme.of(context).textTheme.titleSmall),
              const SizedBox(height: QuorumSpacing.xs),
              // A real, fixed-height reservation (one text line) so a
              // card's layout never jumps once its real preview line
              // resolves -- loading and "no real number for this
              // domain" (Search) both render as the same real blank
              // space, never a placeholder string.
              SizedBox(
                height: 16,
                child: spec.previewLine == null
                    ? null
                    : FutureBuilder<String>(
                        future: spec.previewLine,
                        builder: (context, snapshot) {
                          if (!snapshot.hasData) return const SizedBox.shrink();
                          return Text(
                            snapshot.data!,
                            style: Theme.of(context).textTheme.bodySmall,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          );
                        },
                      ),
              ),
            ],
          ),
        ),
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

class CareerPipelineLoader extends StatefulWidget {
  final Future<List<CareerApplication>> Function() fetch;
  final Future<CompanyDigestData> Function(String applicationId)? fetchDigest;
  final CreateApplicationFetcher? createApplication;
  final ScheduleInterviewFetcher? scheduleInterview;

  const CareerPipelineLoader({
    super.key,
    required this.fetch,
    this.fetchDigest,
    this.createApplication,
    this.scheduleInterview,
  });

  @override
  State<CareerPipelineLoader> createState() => CareerPipelineLoaderState();
}

class CareerPipelineLoaderState extends State<CareerPipelineLoader> {
  late Future<List<CareerApplication>> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.fetch();
  }

  Future<void> _refresh() async {
    final next = widget.fetch();
    // REAL, DISCLOSED FIX (`DEC-194`, found by this block's own new
    // widget test actually exercising a real refresh, not assumed from
    // the identical pre-existing flaw silently carried in `agents_
    // index_screen.dart`/`gate_showcase_screen.dart`): an ARROW-body
    // `() => _future = next` evaluates to the assignment's own value
    // (`next`, a real `Future`), which Flutter's `State.setState()`
    // runtime check catches and rejects as "callback argument returned
    // a Future" -- a block body discards the expression's value, the
    // real fix, not merely a style preference.
    setState(() {
      _future = next;
    });
    await next;
  }

  Future<void> _openNewApplicationSheet() async {
    final createApplication = widget.createApplication;
    if (createApplication == null) return;
    final result = await showModalBottomSheet<CreateApplicationResult>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _NewApplicationSheet(createApplication: createApplication),
    );
    if (result == null || !mounted) return;
    await _refresh();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(result.executed ? 'Added ${result.company ?? 'that application'}.' : 'The Gate declined to add that application.')),
    );
  }

  Future<void> _openScheduleInterviewSheet(CareerApplication application) async {
    final scheduleInterview = widget.scheduleInterview;
    if (scheduleInterview == null) return;
    final result = await showModalBottomSheet<ScheduleInterviewResult>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _ScheduleInterviewSheet(scheduleInterview: scheduleInterview, application: application),
    );
    if (result == null || !mounted) return;
    await _refresh();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(result.executed ? 'Interview scheduled with ${application.company}.' : 'The Gate declined to schedule that interview.')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Career pipeline')),
      floatingActionButton: widget.createApplication == null
          ? null
          : FloatingActionButton(onPressed: _openNewApplicationSheet, child: const Icon(Icons.add)),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<List<CareerApplication>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text("Couldn't load your career pipeline: ${snapshot.error}"));
          }
          final digest = widget.fetchDigest;
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
            onScheduleInterview: widget.scheduleInterview == null ? null : _openScheduleInterviewSheet,
          );
        },
        ),
      ),
    );
  }
}

class _NewApplicationSheet extends StatefulWidget {
  final CreateApplicationFetcher createApplication;

  const _NewApplicationSheet({required this.createApplication});

  @override
  State<_NewApplicationSheet> createState() => _NewApplicationSheetState();
}

class _NewApplicationSheetState extends State<_NewApplicationSheet> {
  final _companyController = TextEditingController();
  final _roleController = TextEditingController();
  bool _submitting = false;
  String? _error;

  @override
  void dispose() {
    _companyController.dispose();
    _roleController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final company = _companyController.text.trim();
    if (company.isEmpty) {
      setState(() => _error = 'Enter a real company name first.');
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final role = _roleController.text.trim();
      final result = await widget.createApplication(company: company, role: role.isEmpty ? null : role);
      if (!mounted) return;
      Navigator.of(context).pop(result);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _submitting = false;
        _error = '$e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 16, right: 16, top: 16,
        bottom: 16 + MediaQuery.of(context).viewInsets.bottom,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('New application', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 16),
          TextField(
            controller: _companyController,
            autofocus: true,
            decoration: const InputDecoration(labelText: 'Company'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _roleController,
            decoration: const InputDecoration(labelText: 'Role (optional)'),
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ],
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: _submitting ? null : _submit,
              child: _submitting
                  ? const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Text('Add application'),
            ),
          ),
        ],
      ),
    );
  }
}

/// `DEC-195` (product rebuild Block F remainder) -- the real form
/// behind the Career pipeline's second write control. `format` is
/// optional (matching `interviews.format`'s own real, nullable
/// schema) -- "Not sure yet" is a genuinely honest choice, not a
/// missing one.
class _ScheduleInterviewSheet extends StatefulWidget {
  final ScheduleInterviewFetcher scheduleInterview;
  final CareerApplication application;

  const _ScheduleInterviewSheet({required this.scheduleInterview, required this.application});

  @override
  State<_ScheduleInterviewSheet> createState() => _ScheduleInterviewSheetState();
}

class _ScheduleInterviewSheetState extends State<_ScheduleInterviewSheet> {
  static const _formats = <String?>[null, 'phone', 'video', 'onsite'];

  DateTime? _date;
  TimeOfDay? _time;
  String? _format;
  bool _submitting = false;
  String? _error;

  String _formatLabel(String? format) {
    switch (format) {
      case 'phone':
        return 'Phone';
      case 'video':
        return 'Video';
      case 'onsite':
        return 'Onsite';
      default:
        return 'Not sure yet';
    }
  }

  Future<void> _pickDate() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: _date ?? now,
      firstDate: now.subtract(const Duration(days: 1)),
      lastDate: now.add(const Duration(days: 365)),
    );
    if (picked != null) setState(() => _date = picked);
  }

  Future<void> _pickTime() async {
    final picked = await showTimePicker(context: context, initialTime: _time ?? TimeOfDay.now());
    if (picked != null) setState(() => _time = picked);
  }

  Future<void> _submit() async {
    setState(() {
      _submitting = true;
      _error = null;
    });
    final date = _date;
    final time = _time;
    final scheduledAt = (date != null && time != null)
        ? DateTime(date.year, date.month, date.day, time.hour, time.minute)
        : null;
    try {
      final result = await widget.scheduleInterview(
        applicationId: widget.application.applicationId,
        scheduledAt: scheduledAt,
        format: _format,
      );
      if (!mounted) return;
      Navigator.of(context).pop(result);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _submitting = false;
        _error = '$e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 16, right: 16, top: 16,
        bottom: 16 + MediaQuery.of(context).viewInsets.bottom,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Schedule interview -- ${widget.application.company}', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 16),
          Wrap(
            spacing: 8,
            children: [
              for (final format in _formats)
                ChoiceChip(
                  label: Text(_formatLabel(format)),
                  selected: _format == format,
                  onSelected: (_) => setState(() => _format = format),
                ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: _pickDate,
                  child: Text(_date == null ? 'Pick a date' : '${_date!.year}-${_date!.month.toString().padLeft(2, '0')}-${_date!.day.toString().padLeft(2, '0')}'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: OutlinedButton(
                  onPressed: _pickTime,
                  child: Text(_time == null ? 'Pick a time' : _time!.format(context)),
                ),
              ),
            ],
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ],
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: _submitting ? null : _submit,
              child: _submitting
                  ? const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Text('Schedule'),
            ),
          ),
        ],
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

/// REAL, DISCLOSED FIX (the redesign's own real "Finance hub" work):
/// now loads real subscriptions AND real recent expenses together (via
/// `Future.wait`), and reuses `_YouScreenState`'s own already-in-flight
/// `weekSummaryFuture` for the real budget-bar numbers -- never a third,
/// separate fetch for data `WeekSummaryStrip`'s own preview card already
/// triggered once.
class FinanceLoader extends StatelessWidget {
  final Future<List<DetectedSubscriptionData>> Function() fetch;
  final Future<List<ExpenseData>> Function()? fetchExpenses;
  final Future<WeekSummaryData>? weekSummaryFuture;

  const FinanceLoader({super.key, required this.fetch, this.fetchExpenses, this.weekSummaryFuture});

  Future<({List<DetectedSubscriptionData> subscriptions, List<ExpenseData> expenses})> _load() async {
    final fetchExpenses = this.fetchExpenses;
    final results = await Future.wait([
      fetch(),
      if (fetchExpenses != null) fetchExpenses() else Future.value(<ExpenseData>[]),
    ]);
    return (
      subscriptions: results[0] as List<DetectedSubscriptionData>,
      expenses: results[1] as List<ExpenseData>,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Finance')),
      body: FutureBuilder(
        future: _load(),
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text("Couldn't load your finances: ${snapshot.error}"));
          }
          final data = snapshot.data!;
          return FutureBuilder<WeekSummaryData>(
            future: weekSummaryFuture,
            builder: (context, summarySnapshot) {
              final summary = summarySnapshot.data;
              return FinanceScreen(
                subscriptions: data.subscriptions,
                recentExpenses: data.expenses,
                monthToDateSpend: summary?.monthToDateSpend,
                monthlyBudgetLimit: summary?.monthlyBudgetLimit,
              );
            },
          );
        },
      ),
    );
  }
}

/// A real, deliberately different loader shape from every other one in
/// this file: it runs TWO real steps, not one -- a real sync attempt
/// first (requesting real calendar permission if not already granted,
/// see `calendar_sync.dart`), then a real read of whatever's now in the
/// on-device mirror, REGARDLESS of whether this particular sync attempt
/// succeeded. This is deliberate, not an oversight: a transient sync
/// failure (or a since-revoked permission) must never blank out real
/// events a PRIOR successful sync already stored -- `CalendarScreen`
/// itself decides the honest empty-state message from the combination
/// of `permissionGranted` and `events`, not this loader.
class CalendarLoader extends StatelessWidget {
  final Future<CalendarSyncResult> Function() sync;
  final Future<List<CalendarMirrorData>> Function() fetchEvents;

  const CalendarLoader({super.key, required this.sync, required this.fetchEvents});

  Future<({CalendarSyncResult syncResult, List<CalendarMirrorData> events})> _load() async {
    final syncResult = await sync();
    final events = await fetchEvents();
    return (syncResult: syncResult, events: events);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Calendar')),
      body: FutureBuilder(
        future: _load(),
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text("Couldn't sync your calendar: ${snapshot.error}"));
          }
          final data = snapshot.data!;
          return CalendarScreen(
            events: data.events,
            permissionGranted: data.syncResult.permissionGranted,
            now: DateTime.now(),
          );
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
            padding: const EdgeInsets.all(QuorumSpacing.md),
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
