// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this
// file was written. Zero Flutter dependencies (same as the file under
// test) — plain `package:test`, `dart test` is the real verification.
//
// THE REAL, LOAD-BEARING PROPERTY these tests exist to prove: "doesn't
// exist yet" (DigestNotYetAvailableException) and "exists but has zero
// summary points" (hasNoRealContent) are genuinely two different real
// states, tested independently, not two branches that happen to render
// the same way.

import 'package:test/test.dart';

import 'package:quorum_mobile/features/career_digest/career_digest_logic.dart';

void main() {
  group('formatSourceCount', () {
    test('zero sources reads honestly, not "Based on 0 sources"', () {
      expect(formatSourceCount(0), 'No sources yet');
    });

    test('one source uses the real singular form', () {
      expect(formatSourceCount(1), 'Based on 1 source');
    });

    test('multiple sources use the real plural form', () {
      expect(formatSourceCount(3), 'Based on 3 sources');
    });
  });

  group('hasNoRealContent -- only reachable on a real, successful fetch', () {
    test('a real digest with zero summary points is flagged as having no real content', () {
      const digest = CompanyDigestData(company: 'Notion', summaryPoints: [], sourceCount: 0);
      expect(hasNoRealContent(digest), isTrue);
    });

    test('a real digest with real summary points is NOT flagged as empty', () {
      const digest = CompanyDigestData(
        company: 'Notion',
        summaryPoints: ['Raised a Series C round in 2021.'],
        sourceCount: 1,
      );
      expect(hasNoRealContent(digest), isFalse);
    });
  });

  group('DigestNotYetAvailableException -- a real, distinctly catchable type', () {
    test('is thrown and caught as its own specific type, never a generic error', () {
      void throwIt() => throw const DigestNotYetAvailableException('app_1');
      expect(throwIt, throwsA(isA<DigestNotYetAvailableException>()));
    });

    test('carries the real application_id it was thrown for, for diagnosability', () {
      const exception = DigestNotYetAvailableException('app_42');
      expect(exception.toString().contains('app_42'), isTrue);
    });
  });
}
