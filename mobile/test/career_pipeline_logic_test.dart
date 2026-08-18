// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this
// file was written. Zero Flutter dependencies (same as the file under
// test) — plain `package:test`, `dart test` is the real verification.
//
// The real, hand-verified ordering case, confirmed in Python before this
// file was finalized:
//   {offer, ghosted, applied, withdrawn} -> [applied, offer, ghosted, withdrawn]

import 'package:test/test.dart';

import 'package:quorum_mobile/features/career/career_pipeline_logic.dart';

CareerApplication _app(String id, String company, String status) =>
    CareerApplication(applicationId: id, company: company, status: status);

void main() {
  group('statusLabel', () {
    test('applied gets a real, readable label', () {
      expect(statusLabel('applied'), 'Applied');
    });

    test('interview_scheduled gets a real, readable label', () {
      expect(statusLabel('interview_scheduled'), 'Interview scheduled');
    });

    test('offer gets a real, readable label', () {
      expect(statusLabel('offer'), 'Offer');
    });

    test('rejected gets a real, readable label', () {
      expect(statusLabel('rejected'), 'Rejected');
    });

    test('a genuinely unrecognized status de-snakes gracefully -- never raw jargon, never a crash', () {
      final label = statusLabel('phone_screen_pending');
      expect(label, 'Phone Screen Pending');
      expect(label.contains('_'), isFalse);
    });
  });

  group('groupByStatus', () {
    test('groups real applications by their real status string', () {
      final grouped = groupByStatus([
        _app('1', 'Notion', 'applied'),
        _app('2', 'Figma', 'applied'),
        _app('3', 'Stripe', 'offer'),
      ]);

      expect(grouped['applied']!.map((a) => a.company).toList(), ['Notion', 'Figma']);
      expect(grouped['offer']!.map((a) => a.company).toList(), ['Stripe']);
    });

    test('never drops an application whose status is genuinely unrecognized', () {
      final grouped = groupByStatus([_app('1', 'Acme', 'ghosted')]);
      expect(grouped.containsKey('ghosted'), isTrue);
      expect(grouped['ghosted']!.length, 1);
    });
  });

  group('orderedStatusKeys', () {
    test('the real, hand-verified mixed known/unknown case', () {
      final grouped = groupByStatus([
        _app('1', 'A', 'offer'),
        _app('2', 'B', 'ghosted'),
        _app('3', 'C', 'applied'),
        _app('4', 'D', 'withdrawn'),
      ]);

      expect(orderedStatusKeys(grouped), ['applied', 'offer', 'ghosted', 'withdrawn']);
    });

    test('two unrecognized statuses sort deterministically, alphabetically against each other', () {
      final grouped = groupByStatus([
        _app('1', 'A', 'zeta_status'),
        _app('2', 'B', 'alpha_status'),
      ]);

      expect(orderedStatusKeys(grouped), ['alpha_status', 'zeta_status']);
    });

    test('only known statuses present preserves the real canonical order', () {
      final grouped = groupByStatus([
        _app('1', 'A', 'rejected'),
        _app('2', 'B', 'applied'),
      ]);

      expect(orderedStatusKeys(grouped), ['applied', 'rejected']);
    });

    test('only unknown statuses present falls back to pure alphabetical order', () {
      final grouped = groupByStatus([
        _app('1', 'A', 'withdrawn'),
        _app('2', 'B', 'ghosted'),
      ]);

      expect(orderedStatusKeys(grouped), ['ghosted', 'withdrawn']);
    });
  });
}
