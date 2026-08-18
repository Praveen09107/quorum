// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's and
// flutter_riverpod's documented APIs; `flutter run` on a real device or
// emulator is the actual, final verification (MOBILE_01 spec's Step 5).

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:quorum_mobile/shell/main_shell.dart';
import 'package:quorum_mobile/theme/quorum_theme.dart';

void main() {
  runApp(const ProviderScope(child: QuorumApp()));
}

class QuorumApp extends StatelessWidget {
  const QuorumApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Quorum',
      debugShowCheckedModeBanner: false,
      theme: buildQuorumLightTheme(),
      home: const MainShell(),
    );
  }
}
