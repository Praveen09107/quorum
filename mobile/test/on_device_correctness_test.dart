import 'package:test/test.dart';
import 'package:quorum_mobile/features/quick_capture/on_device_correctness.dart';

void main() {
  group('checkOnDeviceExtraction -- domain gate', () {
    test('rejects a missing domain', () {
      final result = checkOnDeviceExtraction({});
      expect(result.passed, isFalse);
    });

    test('rejects an unrecognized domain', () {
      final result = checkOnDeviceExtraction({'domain': 'not_a_real_domain'});
      expect(result.passed, isFalse);
    });
  });

  group('checkOnDeviceExtraction -- tasks', () {
    Map<String, dynamic> validCreate() => {
          'domain': 'tasks',
          'operation': 'create',
          'title': 'Finish the report',
          'estimated_hours': 2.0,
          'deadline_iso': null,
        };

    test('passes a real, ordinary, well-formed task', () {
      expect(checkOnDeviceExtraction(validCreate()).passed, isTrue);
    });

    test('fails a real, on-device-found bug from tonight -- null estimated_hours', () {
      final args = validCreate()..['estimated_hours'] = null;
      final result = checkOnDeviceExtraction(args);
      expect(result.passed, isFalse);
      expect(result.reason, contains('estimated_hours'));
    });

    test('fails a zero estimated_hours', () {
      final args = validCreate()..['estimated_hours'] = 0.0;
      expect(checkOnDeviceExtraction(args).passed, isFalse);
    });

    test('fails a negative estimated_hours', () {
      final args = validCreate()..['estimated_hours'] = -1.0;
      expect(checkOnDeviceExtraction(args).passed, isFalse);
    });

    test('fails a NaN estimated_hours -- the exact real DEC-153 B1 class of bug', () {
      final args = validCreate()..['estimated_hours'] = double.nan;
      expect(checkOnDeviceExtraction(args).passed, isFalse);
    });

    test('fails estimated_hours above the real max bound', () {
      final args = validCreate()..['estimated_hours'] = 1000.0;
      expect(checkOnDeviceExtraction(args).passed, isFalse);
    });

    test('fails an empty title', () {
      final args = validCreate()..['title'] = '   ';
      expect(checkOnDeviceExtraction(args).passed, isFalse);
    });

    test('fails a title over the real max length', () {
      final args = validCreate()..['title'] = 'x' * 501;
      expect(checkOnDeviceExtraction(args).passed, isFalse);
    });

    test('passes a real, parseable deadline_iso', () {
      final args = validCreate()..['deadline_iso'] = '2027-01-01T00:00:00Z';
      expect(checkOnDeviceExtraction(args).passed, isTrue);
    });

    test('fails an unparseable deadline_iso', () {
      final args = validCreate()..['deadline_iso'] = 'next tuesday';
      expect(checkOnDeviceExtraction(args).passed, isFalse);
    });

    test('a real update trusts a non-empty reference_description', () {
      final args = {'domain': 'tasks', 'operation': 'update', 'reference_description': 'the Q3 one'};
      expect(checkOnDeviceExtraction(args).passed, isTrue);
    });

    test('a real delete fails an empty reference_description', () {
      final args = {'domain': 'tasks', 'operation': 'delete', 'reference_description': ''};
      expect(checkOnDeviceExtraction(args).passed, isFalse);
    });
  });

  group('checkOnDeviceExtraction -- finance', () {
    Map<String, dynamic> validLogExpense() => {
          'domain': 'finance',
          'action': 'log_expense',
          'amount': 42.0,
          'category': 'groceries',
          'payee': 'Local Store',
        };

    test('passes a real, ordinary expense', () {
      expect(checkOnDeviceExtraction(validLogExpense()).passed, isTrue);
    });

    test('passes with a real null payee', () {
      final args = validLogExpense()..['payee'] = null;
      expect(checkOnDeviceExtraction(args).passed, isTrue);
    });

    test('fails a null amount -- the exact real on-device-found bug tonight', () {
      final args = validLogExpense()..['amount'] = null;
      expect(checkOnDeviceExtraction(args).passed, isFalse);
    });

    test('fails a zero amount', () {
      final args = validLogExpense()..['amount'] = 0.0;
      expect(checkOnDeviceExtraction(args).passed, isFalse);
    });

    test('fails an amount above the real max bound', () {
      final args = validLogExpense()..['amount'] = 100000000.0;
      expect(checkOnDeviceExtraction(args).passed, isFalse);
    });

    test('fails a missing category', () {
      final args = validLogExpense()..['category'] = null;
      expect(checkOnDeviceExtraction(args).passed, isFalse);
    });

    test('a real update_expense trusts a non-empty reference_description', () {
      final args = {'domain': 'finance', 'action': 'update_expense', 'reference_description': 'that Swiggy expense'};
      expect(checkOnDeviceExtraction(args).passed, isTrue);
    });
  });

  group('checkOnDeviceExtraction -- calendar', () {
    Map<String, dynamic> validCreate() => {
          'domain': 'calendar',
          'operation': 'create',
          'title': 'Call with Jane',
          'start_iso': '2099-01-01T10:00:00+00:00',
          'end_iso': '2099-01-01T10:30:00+00:00',
          'invitee_email': 'jane@company.com',
        };

    test('passes a real, well-formed, future, timezone-aware event', () {
      expect(checkOnDeviceExtraction(validCreate()).passed, isTrue);
    });

    test('fails a naive (no timezone) start_iso', () {
      final args = validCreate()..['start_iso'] = '2099-01-01T10:00:00';
      expect(checkOnDeviceExtraction(args).passed, isFalse);
    });

    test('fails when end is not after start', () {
      final args = validCreate();
      args['end_iso'] = args['start_iso'];
      expect(checkOnDeviceExtraction(args).passed, isFalse);
    });

    test('fails a start that is genuinely in the past', () {
      final args = validCreate()..['start_iso'] = '2020-01-01T10:00:00+00:00';
      expect(checkOnDeviceExtraction(args).passed, isFalse);
    });

    test('fails an unparseable start_iso', () {
      final args = validCreate()..['start_iso'] = 'next tuesday at 3pm';
      expect(checkOnDeviceExtraction(args).passed, isFalse);
    });

    test('fails a title over the real max length', () {
      final args = validCreate()..['title'] = 'x' * 501;
      expect(checkOnDeviceExtraction(args).passed, isFalse);
    });

    test('fails an event exceeding the real max duration', () {
      final args = validCreate()..['end_iso'] = '2099-01-02T10:31:00+00:00'; // > 24h
      expect(checkOnDeviceExtraction(args).passed, isFalse);
    });

    test('fails an invitee_email that does not look like a real email', () {
      final args = validCreate()..['invitee_email'] = 'jane';
      expect(checkOnDeviceExtraction(args).passed, isFalse);
    });

    test('passes with a real null invitee_email', () {
      final args = validCreate()..['invitee_email'] = null;
      expect(checkOnDeviceExtraction(args).passed, isTrue);
    });

    test('fails an unrecognized operation -- calendar only ever supports create', () {
      final args = validCreate()..['operation'] = 'update';
      expect(checkOnDeviceExtraction(args).passed, isFalse);
    });
  });

  group('checkOnDeviceExtraction -- career', () {
    test('passes a real, well-formed status update', () {
      final args = {'domain': 'career', 'operation': 'update', 'reference_description': 'Notion', 'new_status': 'interview_scheduled'};
      expect(checkOnDeviceExtraction(args).passed, isTrue);
    });

    test('fails a missing new_status', () {
      final args = {'domain': 'career', 'operation': 'update', 'reference_description': 'Notion', 'new_status': null};
      expect(checkOnDeviceExtraction(args).passed, isFalse);
    });

    test('fails an unrecognized operation -- career only ever supports update', () {
      final args = {'domain': 'career', 'operation': 'create', 'reference_description': 'Notion', 'new_status': 'rejected'};
      expect(checkOnDeviceExtraction(args).passed, isFalse);
    });
  });

  group('checkOnDeviceExtraction -- email', () {
    test('passes with a real recipient_description and user_intent', () {
      final args = {
        'domain': 'email',
        'operation': 'create',
        'recipient_description': 'Sarah',
        'recipient_email': null,
        'user_intent': 'tell Sarah the proposal looks good',
      };
      expect(checkOnDeviceExtraction(args).passed, isTrue);
    });

    test('passes with a real literal recipient_email and no description', () {
      final args = {
        'domain': 'email',
        'operation': 'create',
        'recipient_description': null,
        'recipient_email': 'sarah@company.com',
        'user_intent': 'tell Sarah the proposal looks good',
      };
      expect(checkOnDeviceExtraction(args).passed, isTrue);
    });

    test('fails with neither a recipient_description nor a recipient_email', () {
      final args = {
        'domain': 'email',
        'operation': 'create',
        'recipient_description': null,
        'recipient_email': null,
        'user_intent': 'tell Sarah the proposal looks good',
      };
      expect(checkOnDeviceExtraction(args).passed, isFalse);
    });

    test('fails a missing user_intent', () {
      final args = {
        'domain': 'email',
        'operation': 'create',
        'recipient_description': 'Sarah',
        'recipient_email': null,
        'user_intent': null,
      };
      expect(checkOnDeviceExtraction(args).passed, isFalse);
    });

    test('fails an unrecognized operation -- email only ever supports create', () {
      final args = {
        'domain': 'email',
        'operation': 'update',
        'recipient_description': 'Sarah',
        'recipient_email': null,
        'user_intent': 'tell Sarah the proposal looks good',
      };
      expect(checkOnDeviceExtraction(args).passed, isFalse);
    });
  });
}
