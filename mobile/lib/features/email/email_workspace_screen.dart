// The real Email agent workspace (`DEC-199`, product rebuild) -- closes
// `DEC-197`'s own disclosed gap: Email has had no real workspace at
// all, only an honest "not built yet" SnackBar on the Agents tab. Every
// real list here comes from data this backend was already writing
// before this session (`action_events`, `sent_messages`) -- the first
// screen to show them together as a real agent's own real tool.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/email/email_overview_logic.dart';
import 'package:quorum_mobile/theme/agent_identity.dart';
import 'package:quorum_mobile/theme/glass.dart';
import 'package:quorum_mobile/theme/quorum_dark_theme.dart';
import 'package:quorum_mobile/theme/quorum_kit.dart';
import 'package:quorum_mobile/theme/spacing.dart';

class EmailWorkspaceScreen extends StatefulWidget {
  final Future<EmailOverviewData> Function() fetch;

  const EmailWorkspaceScreen({super.key, required this.fetch});

  @override
  State<EmailWorkspaceScreen> createState() => _EmailWorkspaceScreenState();
}

class _EmailWorkspaceScreenState extends State<EmailWorkspaceScreen> {
  late Future<EmailOverviewData> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.fetch();
  }

  Future<void> _refresh() async {
    final next = widget.fetch();
    // The same real `DEC-194` arrow-body/Future `setState` fix every
    // sibling screen in this rebuild already applies.
    setState(() {
      _future = next;
    });
    await next;
  }

  @override
  Widget build(BuildContext context) {
    final identity = identityOf(QuorumAgent.email);
    return Scaffold(
      appBar: AppBar(title: const Text('Email agent')),
      body: QuorumAmbientBackground(
        child: SafeArea(
          child: RefreshIndicator(
            onRefresh: _refresh,
            child: FutureBuilder<EmailOverviewData>(
              future: _future,
              builder: (context, snapshot) {
                if (snapshot.connectionState != ConnectionState.done) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snapshot.hasError) {
                  return Center(
                    child: RetryErrorState(
                      message: 'Could not load the real email activity -- ${snapshot.error}',
                      onRetry: () => setState(() {
                        _future = widget.fetch();
                      }),
                    ),
                  );
                }
                final data = snapshot.data!;
                final waiting = awaitingReply(data.sentHistory);
                final now = DateTime.now();
                return ListView(
                  padding: const EdgeInsets.all(QuorumSpacing.md),
                  children: [
                    Row(
                      children: [
                        const AgentBadge(agent: QuorumAgent.email),
                        const SizedBox(width: QuorumSpacing.sm),
                        Expanded(
                          child: Text(
                            'Real Gmail drafts and sends this agent has actually produced -- nothing here is simulated.',
                            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: QuorumDarkGround.textSecondary),
                          ),
                        ),
                      ],
                    ),
                    SectionHeader(label: 'Awaiting reply', accent: identity.accent),
                    if (waiting.isEmpty)
                      const HonestEmptyState(
                        icon: Icons.mark_email_read_outlined,
                        headline: 'Nothing waiting on a reply',
                        detail: 'Every real sent message in this history has a real reply, or nothing has been sent yet.',
                      )
                    else
                      GlassPanel(
                        accent: identity.accent,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            for (var i = 0; i < waiting.length; i++) ...[
                              if (i > 0) const Divider(height: QuorumSpacing.md),
                              _SentMessageRow(message: waiting[i], now: now),
                            ],
                          ],
                        ),
                      ),
                    SectionHeader(label: 'Drafts this agent created', accent: identity.accent),
                    if (data.drafts.isEmpty)
                      const HonestEmptyState(
                        icon: Icons.drafts_outlined,
                        headline: 'No real drafts yet',
                        detail: 'When this agent drafts a reply, it lands in your real Gmail Drafts folder with no approval needed -- it will show up here too.',
                      )
                    else
                      GlassPanel(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            for (var i = 0; i < data.drafts.length; i++) ...[
                              if (i > 0) const Divider(height: QuorumSpacing.md),
                              _DraftRow(draft: data.drafts[i], now: now),
                            ],
                          ],
                        ),
                      ),
                    SectionHeader(label: 'Sent history', accent: identity.accent),
                    if (data.sentHistory.isEmpty)
                      const HonestEmptyState(
                        icon: Icons.outbox_outlined,
                        headline: 'Nothing sent yet',
                        detail: 'Real sent messages this agent genuinely detected will appear here.',
                      )
                    else
                      GlassPanel(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            for (var i = 0; i < data.sentHistory.length; i++) ...[
                              if (i > 0) const Divider(height: QuorumSpacing.md),
                              _SentMessageRow(message: data.sentHistory[i], now: now, showStatus: true),
                            ],
                          ],
                        ),
                      ),
                    SectionHeader(label: 'Known recipients', accent: identity.accent),
                    if (data.knownRecipients.isEmpty)
                      const HonestEmptyState(
                        icon: Icons.contacts_outlined,
                        headline: 'No one you\'ve genuinely emailed yet',
                        detail: 'Every real address you\'ve sent to will build up a real trust list here.',
                      )
                    else
                      GlassPanel(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            for (var i = 0; i < data.knownRecipients.length; i++) ...[
                              if (i > 0) const Divider(height: QuorumSpacing.md),
                              _KnownRecipientRow(recipient: data.knownRecipients[i], now: now),
                            ],
                          ],
                        ),
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

class _SentMessageRow extends StatelessWidget {
  final SentMessageData message;
  final DateTime now;
  final bool showStatus;

  const _SentMessageRow({required this.message, required this.now, this.showStatus = false});

  @override
  Widget build(BuildContext context) {
    final replied = !isAwaitingReply(message);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: QuorumSpacing.xs),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(message.subject, style: Theme.of(context).textTheme.titleSmall?.copyWith(color: QuorumDarkGround.textPrimary)),
                const SizedBox(height: 2),
                Text(message.recipient, style: Theme.of(context).textTheme.bodySmall?.copyWith(color: QuorumDarkGround.textSecondary)),
                const SizedBox(height: 2),
                Text(formatRelativeDays(message.sentAt, now), style: QuorumMono.detail(context)),
              ],
            ),
          ),
          if (showStatus) ...[
            const SizedBox(width: QuorumSpacing.sm),
            StatusPill(
              label: replied ? 'Replied' : 'Awaiting reply',
              icon: replied ? Icons.check_circle_rounded : Icons.hourglass_empty_rounded,
              color: replied ? QuorumDarkStatus.verified : QuorumDarkStatus.needsAttention,
            ),
          ],
        ],
      ),
    );
  }
}

class _DraftRow extends StatelessWidget {
  final EmailDraftData draft;
  final DateTime now;

  const _DraftRow({required this.draft, required this.now});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: QuorumSpacing.xs),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  draft.subject ?? '(no subject)',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(color: QuorumDarkGround.textPrimary),
                ),
                const SizedBox(height: 2),
                Text('To: ${draft.recipient}', style: Theme.of(context).textTheme.bodySmall?.copyWith(color: QuorumDarkGround.textSecondary)),
                const SizedBox(height: 2),
                Text(formatRelativeDays(draft.createdAt, now), style: QuorumMono.detail(context)),
              ],
            ),
          ),
          const SizedBox(width: QuorumSpacing.sm),
          const StatusPill(label: 'Draft', icon: Icons.drafts_rounded, color: QuorumDarkStatus.neutral),
        ],
      ),
    );
  }
}

class _KnownRecipientRow extends StatelessWidget {
  final KnownRecipientData recipient;
  final DateTime now;

  const _KnownRecipientRow({required this.recipient, required this.now});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: QuorumSpacing.xs),
      child: Row(
        children: [
          Expanded(
            child: Text(recipient.recipient, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: QuorumDarkGround.textPrimary)),
          ),
          Text(
            '${formatMessageCount(recipient.messageCount)} · ${formatRelativeDays(recipient.lastContactedAt, now)}',
            style: QuorumMono.detail(context),
          ),
        ],
      ),
    );
  }
}
