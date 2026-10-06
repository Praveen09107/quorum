// The real Google-connection health screen (`DEC-198`, product
// rebuild) -- the direct, disclosed answer to this rebuild's own
// sharpest named root cause: a real, expired or revoked Google grant
// silently dams the entire Gmail/Calendar/Career surface, and nothing
// anywhere in this app has ever told a signed-in user that's what
// happened, or even that Quorum requests Gmail/Calendar access at all.
//
// Reuses the real, already-live sign-in flow for "Reconnect" --
// `AuthController.signIn()` always carries `access_type=offline`/
// `prompt=consent` (`auth_controller.dart`), so a repeat real consent
// genuinely re-issues a fresh refresh_token; no separate reconnect
// plumbing was built or is needed.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/connections/connections_logic.dart';
import 'package:quorum_mobile/theme/glass.dart';
import 'package:quorum_mobile/theme/quorum_dark_theme.dart';
import 'package:quorum_mobile/theme/quorum_kit.dart';
import 'package:quorum_mobile/theme/spacing.dart';

class ConnectionsScreen extends StatefulWidget {
  final Future<ConnectionHealthData> Function() fetch;
  final Future<void> Function() onReconnect;

  const ConnectionsScreen({super.key, required this.fetch, required this.onReconnect});

  @override
  State<ConnectionsScreen> createState() => _ConnectionsScreenState();
}

class _ConnectionsScreenState extends State<ConnectionsScreen> {
  late Future<ConnectionHealthData> _future;
  bool _reconnecting = false;

  @override
  void initState() {
    super.initState();
    _future = widget.fetch();
  }

  Future<void> _refresh() async {
    final next = widget.fetch();
    // The same real `DEC-194` arrow-body/Future `setState` fix every
    // sibling screen in this rebuild already applies -- a block body
    // here, never `setState(() => _future = next)`.
    setState(() {
      _future = next;
    });
    await next;
  }

  Future<void> _handleReconnect() async {
    setState(() => _reconnecting = true);
    String? error;
    try {
      await widget.onReconnect();
    } catch (e) {
      error = 'Reconnecting to Google failed: $e';
    }
    if (!mounted) return;
    setState(() => _reconnecting = false);
    if (error != null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error)));
      return;
    }
    await _refresh();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Google connection')),
      body: QuorumAmbientBackground(
        child: SafeArea(
          child: RefreshIndicator(
            onRefresh: _refresh,
            child: FutureBuilder<ConnectionHealthData>(
              future: _future,
              builder: (context, snapshot) {
                if (snapshot.connectionState != ConnectionState.done) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snapshot.hasError) {
                  return Center(
                    child: RetryErrorState(
                      message: 'Could not load your Google connection status -- ${snapshot.error}',
                      onRetry: () => setState(() {
                        _future = widget.fetch();
                      }),
                    ),
                  );
                }
                final data = snapshot.data!;
                final status = describeConnectionStatus(data);
                return ListView(
                  padding: const EdgeInsets.all(QuorumSpacing.md),
                  children: [
                    _StatusCard(data: data, status: status),
                    const SizedBox(height: QuorumSpacing.md),
                    if (status != ConnectionStatus.healthy)
                      FilledButton.icon(
                        onPressed: _reconnecting ? null : _handleReconnect,
                        icon: _reconnecting
                            ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                            : const Icon(Icons.link_rounded),
                        label: Text(status == ConnectionStatus.notConnected ? 'Connect Google' : 'Reconnect'),
                      ),
                    if (status != ConnectionStatus.healthy) const SizedBox(height: QuorumSpacing.md),
                    if (data.grantedScopes.isNotEmpty) ...[
                      const SectionHeader(label: 'What Quorum can access', accent: QuorumDarkStatus.verified),
                      GlassPanel(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            for (var i = 0; i < data.grantedScopes.length; i++) ...[
                              if (i > 0) const Divider(height: QuorumSpacing.md),
                              Row(
                                children: [
                                  const Icon(Icons.check_circle_outline_rounded, size: 18, color: QuorumDarkStatus.verified),
                                  const SizedBox(width: QuorumSpacing.sm),
                                  Expanded(
                                    child: Text(
                                      humanizeScope(data.grantedScopes[i]),
                                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: QuorumDarkGround.textPrimary),
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ],
                        ),
                      ),
                    ] else
                      const HonestEmptyState(
                        icon: Icons.link_off_rounded,
                        headline: 'No Google access granted yet',
                        detail:
                            'Connect your Google account so Quorum\'s agents can genuinely read and send email, and create calendar events on your behalf.',
                      ),
                  ],
                );
              },
            ),
          ),
        ),
      ),
    );
  }
}

class _StatusCard extends StatelessWidget {
  final ConnectionHealthData data;
  final ConnectionStatus status;

  const _StatusCard({required this.data, required this.status});

  @override
  Widget build(BuildContext context) {
    final (icon, color) = switch (status) {
      ConnectionStatus.healthy => (Icons.verified_rounded, QuorumDarkStatus.verified),
      ConnectionStatus.needsReconnect => (Icons.warning_amber_rounded, QuorumDarkStatus.needsAttention),
      ConnectionStatus.notConnected => (Icons.link_off_rounded, QuorumDarkStatus.neutral),
    };
    return GlassPanel(
      accent: color,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          StatusPill(label: connectionStatusHeadline(status), icon: icon, color: color, emphasized: true),
          if (status == ConnectionStatus.needsReconnect) ...[
            const SizedBox(height: QuorumSpacing.sm),
            Text(
              'Quorum still has a record of your Google access, but it could not be used just now -- '
              'this usually means the grant expired or was revoked. Reconnect to restore email and calendar actions.',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: QuorumDarkGround.textSecondary),
            ),
          ],
          if (status == ConnectionStatus.notConnected) ...[
            const SizedBox(height: QuorumSpacing.sm),
            Text(
              'Quorum has no real Google access on file -- email drafting, sending, and calendar booking stay '
              'unavailable until you connect.',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: QuorumDarkGround.textSecondary),
            ),
          ],
          if (data.lastUpdatedAt != null) ...[
            const SizedBox(height: QuorumSpacing.sm),
            Text(formatLastUpdated(data.lastUpdatedAt!, DateTime.now()), style: QuorumMono.detail(context)),
          ],
        ],
      ),
    );
  }
}
