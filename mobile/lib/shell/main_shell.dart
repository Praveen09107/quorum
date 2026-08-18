// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented
// `NavigationBar`/`StatefulWidget` API; `flutter test` on a real machine
// is the actual verification.
//
// HONEST STATUS, specific to this repository: this file is the real,
// original MOBILE_01 scaffold — four stable tabs with placeholder content
// only. A batch-guide document accompanying this session claimed
// main_shell.dart "was substantially rewritten during MOBILE_22 (screen
// composition)" and instructed reading "the REAL, current file" as if
// that rewrite had already happened here. It hasn't: MOBILE_22 has not
// been built in this repository — the mobile session sequence starts at
// this file. See DECISIONS_LOG.md for the full disclosure. Real screen
// content for any of the four tabs is explicitly out of scope for this
// session (MOBILE_05 onward); building it now would mean guessing at
// specs that come later.
//
// Four stable tabs, fixed navigation position — a deliberate choice over
// an adaptive-navigation-position pattern (ADD §12.3): adaptive *content*
// works, adaptive *navigation position* confuses users. Today, Log,
// Trust, You — exact names and order from ADD §12.3.

import 'package:flutter/material.dart';

class MainShell extends StatefulWidget {
  const MainShell({super.key});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _selectedIndex = 0;

  static const List<_QuorumTab> _tabs = [
    _QuorumTab(label: 'Today', icon: Icons.today_outlined, selectedIcon: Icons.today),
    _QuorumTab(label: 'Log', icon: Icons.history_outlined, selectedIcon: Icons.history),
    _QuorumTab(label: 'Trust', icon: Icons.verified_outlined, selectedIcon: Icons.verified),
    _QuorumTab(label: 'You', icon: Icons.person_outline, selectedIcon: Icons.person),
  ];

  void _onDestinationSelected(int index) {
    setState(() {
      _selectedIndex = index;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: _PlaceholderTabContent(tab: _tabs[_selectedIndex]),
      ),
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

/// Deliberately minimal — real screen content for any tab is out of
/// scope for this session (MOBILE_05 onward builds Today; later sessions
/// build Log/Trust/You). This exists only to prove tab-switching works.
class _PlaceholderTabContent extends StatelessWidget {
  final _QuorumTab tab;

  const _PlaceholderTabContent({required this.tab});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Text(
        '${tab.label} tab',
        key: Key('placeholder_${tab.label.toLowerCase()}'),
        style: Theme.of(context).textTheme.headlineSmall,
      ),
    );
  }
}
