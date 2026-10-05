// Onboarding (`DEC-196`, product rebuild Block G) -- never built before
// this session (ADD §12.5's own standing gap). Three swipeable glass
// cards over the real ambient background every other dark-theme screen
// already uses, then a direct hand-off into the capture flow -- "show,
// don't tell" is the whole point: the first real thing a new user sees
// after this screen is the Gate pipeline genuinely running, not a
// fourth slide describing it.
//
// Shown exactly once per real, signed-in account -- `OnboardingStore`
// (new, `flutter_secure_storage`-backed, no new native dependency) is
// the real, on-device record of that. `onDone` is a plain, injected
// callback (this screen never marks itself seen; the caller owns that
// decision, matching every other real/external boundary in this app).

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

import 'package:quorum_mobile/theme/agent_identity.dart';
import 'package:quorum_mobile/theme/glass.dart';
import 'package:quorum_mobile/theme/quorum_dark_theme.dart';
import 'package:quorum_mobile/theme/quorum_kit.dart';
import 'package:quorum_mobile/theme/spacing.dart';

class _OnboardingCard {
  final IconData icon;
  final Color accent;
  final String title;
  final String body;
  final bool showAgentBadges;

  const _OnboardingCard({
    required this.icon,
    required this.accent,
    required this.title,
    required this.body,
    this.showAgentBadges = false,
  });
}

const _cards = [
  _OnboardingCard(
    icon: Icons.smart_toy_outlined,
    accent: Color(0xFF4A9EFF),
    title: 'Five agents work on your behalf',
    body: 'Email, Calendar, Tasks, Finance, and Career each have a real agent that drafts, schedules, and tracks things for you.',
    showAgentBadges: true,
  ),
  _OnboardingCard(
    icon: Icons.shield_outlined,
    accent: QuorumDarkStatus.verified,
    title: 'A Gate verifies every one of them',
    body: 'Before anything happens, a real verification pipeline checks it against your actual data -- not a guess, a lookup.',
  ),
  _OnboardingCard(
    icon: Icons.pan_tool_outlined,
    accent: QuorumDarkStatus.needsAttention,
    title: 'Anything irreversible always waits for you',
    body: 'Sending a real email or booking a real external meeting always asks first. No exception, in any mode.',
  ),
];

class OnboardingScreen extends StatefulWidget {
  final VoidCallback onDone;

  const OnboardingScreen({super.key, required this.onDone});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final _controller = PageController();
  int _page = 0;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _next() {
    if (_page == _cards.length - 1) {
      widget.onDone();
      return;
    }
    _controller.nextPage(duration: const Duration(milliseconds: 300), curve: Curves.easeOut);
  }

  @override
  Widget build(BuildContext context) {
    final isLast = _page == _cards.length - 1;
    return QuorumAmbientBackground(
      accent: _cards[_page].accent,
      child: SafeArea(
        child: Column(
          children: [
            Align(
              alignment: Alignment.topRight,
              child: Padding(
                padding: const EdgeInsets.all(QuorumSpacing.md),
                child: TextButton(onPressed: widget.onDone, child: const Text('Skip')),
              ),
            ),
            Expanded(
              child: PageView(
                controller: _controller,
                onPageChanged: (index) => setState(() => _page = index),
                children: [for (final card in _cards) _OnboardingCardView(card: card)],
              ),
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                for (var i = 0; i < _cards.length; i++)
                  AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    margin: const EdgeInsets.symmetric(horizontal: 4),
                    width: i == _page ? 24 : 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: i == _page ? _cards[_page].accent : QuorumDarkGround.textTertiary,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
              ],
            ),
            Padding(
              padding: const EdgeInsets.all(QuorumSpacing.lg),
              child: SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: _next,
                  child: Text(isLast ? 'Get started' : 'Next'),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _OnboardingCardView extends StatelessWidget {
  final _OnboardingCard card;

  const _OnboardingCardView({required this.card});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(QuorumSpacing.lg),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          GlassPanel(
            accent: card.accent,
            padding: const EdgeInsets.all(QuorumSpacing.lg),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(card.icon, size: 56, color: card.accent),
                const SizedBox(height: QuorumSpacing.lg),
                Text(
                  card.title,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(color: QuorumDarkGround.textPrimary),
                ),
                const SizedBox(height: QuorumSpacing.md),
                Text(
                  card.body,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: QuorumDarkGround.textSecondary),
                ),
                if (card.showAgentBadges) ...[
                  const SizedBox(height: QuorumSpacing.lg),
                  Wrap(
                    alignment: WrapAlignment.center,
                    spacing: QuorumSpacing.sm,
                    runSpacing: QuorumSpacing.sm,
                    children: [for (final agent in kDomainAgents) AgentBadge(agent: agent, compact: true)],
                  ),
                ],
              ],
            ),
          ).animate().fadeIn(duration: const Duration(milliseconds: 400)).slideY(begin: 0.08, end: 0),
        ],
      ),
    );
  }
}
