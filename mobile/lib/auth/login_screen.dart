/// The real, live login screen -- the first screen a real user without
/// a stored session sees. Deliberately minimal: one real action (sign
/// in with Google), a real loading state, and a real, honest error
/// message on failure -- no fabricated marketing copy about features
/// that aren't live yet.
library;

import 'package:flutter/material.dart';

import 'auth_controller.dart';

class LoginScreen extends StatefulWidget {
  final AuthController authController;
  final VoidCallback onSignedIn;

  const LoginScreen({super.key, required this.authController, required this.onSignedIn});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  bool _signingIn = false;
  String? _error;

  Future<void> _handleSignIn() async {
    setState(() {
      _signingIn = true;
      _error = null;
    });
    try {
      await widget.authController.signIn();
      if (mounted) widget.onSignedIn();
    } on SignInCancelled {
      // A real, honest cancellation -- not an error state.
      if (mounted) setState(() => _signingIn = false);
    } catch (e) {
      if (mounted) {
        setState(() {
          _signingIn = false;
          _error = 'Sign-in failed: $e';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text('Quorum', style: Theme.of(context).textTheme.headlineMedium),
                const SizedBox(height: 8),
                const Text('Sign in with the real Google account you want Quorum to act on behalf of.', textAlign: TextAlign.center),
                const SizedBox(height: 32),
                if (_signingIn)
                  const CircularProgressIndicator()
                else
                  FilledButton.icon(
                    onPressed: _handleSignIn,
                    icon: const Icon(Icons.login),
                    label: const Text('Sign in with Google'),
                  ),
                if (_error != null) ...[
                  const SizedBox(height: 16),
                  Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error), textAlign: TextAlign.center),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
