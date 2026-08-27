/// Quorum's real app entry point. Batch 10 Phase 3 Part C prerequisite
/// (`DEC-105`): checks for a real, currently-valid session at startup --
/// no stored session (or one that fails to refresh) shows the real
/// `LoginScreen`; a real session goes straight to `MainShell`, wired
/// with every real, live fetcher that exists so far -- `/trust_digest`
/// (`DEC-100`/`DEC-103`), `/trust` (real self-test results against the
/// real Gate, wiring `self_test_harness.py`'s already-real
/// `run_self_test()` into a live route, `DEC-106`), `/tasks` (the real
/// `tasks` table, `DEC-107`), `/career_pipeline` (the real
/// `applications` table, `DEC-108`), `/finance/subscriptions` (a
/// real, disclosed, deliberately simple detection rule over the real
/// `expenses` table -- no `subscription_detective.py` ever existed in
/// this backend despite the spec corpus's own claim otherwise,
/// `DEC-109`), and -- as of `DEC-119` -- `/today`. Wiring `fetchTrust`
/// genuinely unlocked the whole Trust tab in the real running app
/// (`DEC-106`) -- `MainShell`'s `_TrustTab` only renders once its own
/// primary fetcher is non-null. `fetchToday` does the same for the
/// Today tab, which also genuinely unlocks the already-built,
/// already-tested Holding Steady -> Tasks drill-through link
/// (`DEC-096`), gated behind `fetchToday` since `MOBILE_23`. A real,
/// disclosed, honest fact, not a bug: Today's own `needs_you_now`/
/// `in_motion` zones will genuinely, correctly render empty right now
/// -- nothing in this backend yet invokes the Gate against a real,
/// live user action to ever produce a row for either real table in the
/// first place (`DEC-119`'s own full account). `fetchCareerApplications`
/// and `fetchFinance` are different again, and genuinely live: the You
/// tab always renders regardless of which "More" section fetchers are
/// configured, so wiring either one alone makes a real, new screen
/// reachable in the running app (`DEC-108`, `DEC-109`). `fetchSearch`
/// joins them as of Roadmap Phase 4a -- real, live, per-user-scoped
/// `GET /search?q=...`, backed by a real Gemini embedding call and a
/// real pgvector similarity query (`features/search.py`), reaching the
/// You tab's already-built Search screen for the first time.
/// `fetchNegotiation` closes a real gap found while scoping the demo
/// dataset session: `NegotiationBundle` has existed as a real, tested
/// mobile type since `MOBILE_09`, but no real backend contract for
/// viewing a negotiation's positions/options -- and no real, live
/// LLM-generated content to populate them with -- ever existed until
/// this session (`features/negotiation_detail.py`, `negotiation/
/// gemini_calls.py`, the first real Stage-B-style LLM content-
/// generation call this backend has ever made). Wiring it genuinely
/// unlocks the Today tab's In Motion cards as real, tappable drill-
/// throughs for the first time, not just a static display.
/// `fetchWaitingOn` joins them as of Phase 4 (`features/waiting_on.py`,
/// `features/email_ingestion.py`) -- real, live, per-user-scoped
/// `GET /waiting_on`, backed by a real Gmail polling job, reaching the
/// You tab's already-built, already-tested Waiting On screen (`_WaitingOnLoader`
/// in `you_screen.dart`) for the first time since it was written years
/// ahead of any real backend to call.
/// `fetchHonestyFeed` joins them as of Phase 6 (`features/honesty_log.py`)
/// -- real, live, per-user-scoped `GET /honesty_log`, closing the real,
/// permanently-dead "Log" bottom-nav tab for the first time since
/// `honesty_log_logic.dart`/`honesty_log_screen.dart` were built years
/// ahead of any real backend to call (Batch 8, `DEC-087`).
/// `fetchGateReveal` joins them as of the same phase (`features/
/// gate_reveal.py`) -- real, live, per-user-scoped `GET /gate_reveal/
/// {proposal_id}`, backed by the Gate's own real findings/objections
/// (now genuinely persisted onto `action_events`, migration `0013`),
/// closing the real, disclosed `DEC-126` gap and making a "Needs you
/// now" card's own tap-through to `gate_reveal_screen.dart` genuinely
/// reachable for the first time since Batch 6 (`DEC-080`).
/// `confirmDelete` is real and live too, as of `DEC-113` -- the real,
/// irreversible `DELETE /account`, unblocked only once real user
/// provisioning existed (`DEC-110`) to make a correctly per-user-scoped
/// deletion possible at all. Every other `MainShell` fetcher stays
/// unconfigured, honestly, until its own backend endpoint exists (Part
/// C-2, tracked in `STATUS_INDEX.md`).
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/account_api.dart';
import 'package:quorum_mobile/api/career_pipeline_api.dart';
import 'package:quorum_mobile/api/finance_api.dart';
import 'package:quorum_mobile/api/gate_reveal_api.dart';
import 'package:quorum_mobile/api/honesty_log_api.dart';
import 'package:quorum_mobile/api/negotiation_api.dart';
import 'package:quorum_mobile/api/search_api.dart';
import 'package:quorum_mobile/api/tasks_api.dart';
import 'package:quorum_mobile/api/today_api.dart';
import 'package:quorum_mobile/api/trust_api.dart';
import 'package:quorum_mobile/api/trust_digest_api.dart';
import 'package:quorum_mobile/api/waiting_on_api.dart';
import 'package:quorum_mobile/auth/auth_api.dart';
import 'package:quorum_mobile/auth/auth_controller.dart';
import 'package:quorum_mobile/auth/login_screen.dart';
import 'package:quorum_mobile/auth/token_store.dart';
import 'package:quorum_mobile/config/api_config.dart';
import 'package:quorum_mobile/features/you/you_logic.dart';
import 'package:quorum_mobile/shell/main_shell.dart';
import 'package:quorum_mobile/theme/quorum_theme.dart';

void main() {
  runApp(const ProviderScope(child: QuorumApp()));
}

class QuorumApp extends StatefulWidget {
  const QuorumApp({super.key});

  @override
  State<QuorumApp> createState() => _QuorumAppState();
}

enum _SessionState { checking, signedOut, signedIn }

class _QuorumAppState extends State<QuorumApp> {
  // One real, shared, long-lived client for the whole app's session --
  // created once here (this widget owns its lifecycle, closed in
  // dispose()), never a hidden singleton a feature module creates for
  // itself. Same discipline `trust_digest_api.dart`'s own real
  // client-injection fix already established this session.
  final http.Client _httpClient = http.Client();
  late final AuthController _authController;
  _SessionState _sessionState = _SessionState.checking;

  @override
  void initState() {
    super.initState();
    _authController = AuthController(
      api: AuthApi(client: _httpClient),
      saveTokens: const TokenStore().save,
      readTokens: const TokenStore().read,
      clearTokens: const TokenStore().clear,
      googleClientId: ApiConfig.googleOAuthClientId,
    );
    _checkForRealExistingSession();
  }

  @override
  void dispose() {
    _httpClient.close();
    super.dispose();
  }

  Future<void> _checkForRealExistingSession() async {
    final token = await _authController.getValidAccessToken();
    if (!mounted) return;
    setState(() => _sessionState = token != null ? _SessionState.signedIn : _SessionState.signedOut);
  }

  Future<void> _handleSignOut() async {
    await _authController.signOut();
    if (!mounted) return;
    setState(() => _sessionState = _SessionState.signedOut);
  }

  /// Real, irreversible (`DEC-113`) -- unlike `_handleSignOut` above,
  /// this deliberately does NOT force an immediate transition back to
  /// `LoginScreen`: `you_screen.dart`'s own real confirmation message
  /// (the actual `DeletionResult` counts) needs to stay on screen long
  /// enough for a person to read it, not be torn down the instant
  /// deletion succeeds. Local tokens are cleared only after the real
  /// server call actually succeeds -- correcting an earlier, inaccurate
  /// version of this comment that claimed tokens were cleared
  /// "immediately regardless" of outcome. That was never what the code
  /// below does, and it must never be "fixed" to match: on a thrown
  /// `ApiException` this method never reaches the clear line, so a
  /// failed deletion attempt correctly leaves the device's session
  /// intact rather than stranding a user who was never actually
  /// deleted server-side.
  Future<DeletionResultData> _handleAccountDeletion() async {
    final result = await createAccountDeletionConfirmer(
      getAccessToken: _authController.getValidAccessToken,
      client: _httpClient,
    )();
    await const TokenStore().clear();
    return result;
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Quorum',
      debugShowCheckedModeBanner: false,
      theme: buildQuorumLightTheme(),
      home: switch (_sessionState) {
        _SessionState.checking => const _SplashScreen(),
        _SessionState.signedOut => LoginScreen(
            authController: _authController,
            onSignedIn: () => setState(() => _sessionState = _SessionState.signedIn),
          ),
        _SessionState.signedIn => MainShell(
            fetchToday: createTodayFetcher(
              getAccessToken: _authController.getValidAccessToken,
              client: _httpClient,
            ),
            fetchTrust: createTrustFetcher(
              getAccessToken: _authController.getValidAccessToken,
              client: _httpClient,
            ),
            fetchTrustDigest: createTrustDigestFetcher(
              getAccessToken: _authController.getValidAccessToken,
              client: _httpClient,
            ),
            fetchTasks: createTasksFetcher(
              getAccessToken: _authController.getValidAccessToken,
              client: _httpClient,
            ),
            fetchCareerApplications: createCareerPipelineFetcher(
              getAccessToken: _authController.getValidAccessToken,
              client: _httpClient,
            ),
            fetchFinance: createFinanceFetcher(
              getAccessToken: _authController.getValidAccessToken,
              client: _httpClient,
            ),
            fetchSearch: createSearchFetcher(
              getAccessToken: _authController.getValidAccessToken,
              client: _httpClient,
            ),
            fetchNegotiation: createNegotiationFetcher(
              getAccessToken: _authController.getValidAccessToken,
              client: _httpClient,
            ),
            fetchGateReveal: createGateRevealFetcher(
              getAccessToken: _authController.getValidAccessToken,
              client: _httpClient,
            ),
            chooseNegotiation: createChooseNegotiationFetcher(
              getAccessToken: _authController.getValidAccessToken,
              client: _httpClient,
            ),
            fetchWaitingOn: createWaitingOnFetcher(
              getAccessToken: _authController.getValidAccessToken,
              client: _httpClient,
            ),
            fetchHonestyFeed: createHonestyLogFetcher(
              getAccessToken: _authController.getValidAccessToken,
              client: _httpClient,
            ),
            confirmDelete: _handleAccountDeletion,
            onSignOut: _handleSignOut,
          ),
      },
    );
  }
}

/// A real, honest, brief loading state -- the one real, live check
/// (does a stored session actually still refresh) genuinely takes a
/// real network round-trip when a token needs refreshing, never
/// instant.
class _SplashScreen extends StatelessWidget {
  const _SplashScreen();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(body: Center(child: CircularProgressIndicator()));
  }
}
