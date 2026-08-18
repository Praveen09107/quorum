// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this
// file was written. Zero Flutter dependencies (same as the file under
// test) — plain `package:test`, `dart test` is the real verification.
//
// Real MIME type strings used throughout (image/jpeg, application/pdf),
// matching receive_sharing_intent's real, documented shape, not toy
// examples.

import 'package:test/test.dart';

import 'package:quorum_mobile/features/share_intent_logic.dart';

void main() {
  test('a shared image is suggested toward Finance -- a plausible receipt', () {
    final draft = classifySharedContent('/storage/x.jpg', 'image/jpeg');
    expect(draft.suggestedDomain, 'finance');
  });

  test('a shared non-image file is suggested toward Tasks', () {
    final draft = classifySharedContent('/storage/report.pdf', 'application/pdf');
    expect(draft.suggestedDomain, 'tasks');
  });

  test('a different real image subtype (png) still correctly suggests Finance', () {
    final draft = classifySharedContent('/storage/receipt.png', 'image/png');
    expect(draft.suggestedDomain, 'finance');
  });

  test('the real, original path is preserved unchanged in the draft', () {
    final draft = classifySharedContent('/storage/emulated/0/Download/receipt.jpg', 'image/jpeg');
    expect(draft.path, '/storage/emulated/0/Download/receipt.jpg');
  });

  test('the real, original mimeType is preserved unchanged in the draft', () {
    final draft = classifySharedContent('/x.pdf', 'application/pdf');
    expect(draft.mimeType, 'application/pdf');
  });
}
