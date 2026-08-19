/// Quorum's real app entry point. Batch 10 Phase 3 Part C prerequisite
/// (`DEC-105`): checks for a real, currently-valid session at startup --
/// no stored session (or one that fails to refresh) shows the real
/// `LoginScreen`; a real session goes straight to `MainShell`, wired
/// with the one real, live fetcher that exists so far (`/trust_digest`,
/// `DEC-100`/`DEC-103`). Every other `MainShell` fetcher stays
/// unconfigured, honestly, until its own backend endpoint exists
/// (Part C-2, tracked in `STATUS_INDEX.md`) -- exactly the same
/// "real, not fabricated" discipline this whole project holds itself
/// to everywhere else, not silently wired to something that doesn't
/// exist yet just because the login screen now does.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/trust_digest_api.dart';
import 'package:quorum_mobile/auth/auth_api.dart';
import 'package:quorum_mobile/auth/auth_controller.dart';
import 'package:quorum_mobile/auth/login_screen.dart';
import 'package:quorum_mobile/auth/token_store.dart';
import 'package:quorum_mobile/config/api_config.dart';
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
            fetchTrustDigest: createTrustDigestFetcher(
              getAccessToken: _authController.getValidAccessToken,
              client: _httpClient,
            ),
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
