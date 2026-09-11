import 'package:test/test.dart';
import 'package:quorum_mobile/features/quick_capture/quick_capture_logic.dart';
import 'package:quorum_mobile/features/quick_capture/quick_capture_router.dart';

QuickCaptureResultData _fakeResult({String domain = 'tasks'}) => QuickCaptureResultData(
      executed: true,
      decision: 'approve',
      stakes: 'S1',
      domain: domain,
      title: 'fake',
      findings: const [],
    );

void main() {
  group('routeQuickCapture -- trusted on-device path', () {
    test('submits the extracted args directly when the correctness bar passes', () async {
      Map<String, dynamic>? capturedArgs;
      var cloudCalled = false;

      final result = await routeQuickCapture(
        'finish the report, 2 hours',
        onDeviceExtract: (_) async => {
          'domain': 'tasks',
          'operation': 'create',
          'title': 'Finish the report',
          'estimated_hours': 2.0,
          'deadline_iso': null,
        },
        submitExtracted: (args) async {
          capturedArgs = args;
          return _fakeResult();
        },
        submitCloud: (_, {required onDeviceAttempted, onDeviceFailureReason}) async {
          cloudCalled = true;
          return _fakeResult();
        },
      );

      expect(capturedArgs, isNotNull);
      expect(capturedArgs!['title'], 'Finish the report');
      expect(cloudCalled, isFalse);
      expect(result.domain, 'tasks');
    });

    test('a genuine failure from the trusted submission propagates -- never silently retried via cloud', () async {
      var cloudCalled = false;

      expect(
        () => routeQuickCapture(
          'finish the report, 2 hours',
          onDeviceExtract: (_) async => {
            'domain': 'tasks',
            'operation': 'create',
            'title': 'Finish the report',
            'estimated_hours': 2.0,
            'deadline_iso': null,
          },
          submitExtracted: (args) async => throw Exception('real Gate rejection'),
          submitCloud: (_, {required onDeviceAttempted, onDeviceFailureReason}) async {
            cloudCalled = true;
            return _fakeResult();
          },
        ),
        throwsA(isA<Exception>()),
      );
      // A microtask beat so the async fallback path (if wrongly taken)
      // would have run before this assertion -- proves it genuinely never
      // runs, not just that the test happened to check too early.
      await Future<void>.delayed(Duration.zero);
      expect(cloudCalled, isFalse);
    });
  });

  group('routeQuickCapture -- real, honest fallback to cloud', () {
    test('falls back to cloud with the real correctness-bar reason when the on-device result is malformed', () async {
      String? capturedText;
      var capturedAttempted = false;
      String? capturedReason;

      final result = await routeQuickCapture(
        'finish the report',
        onDeviceExtract: (_) async => {
          'domain': 'tasks',
          'operation': 'create',
          'title': 'Finish the report',
          'estimated_hours': null, // the real, on-device-found bug class from tonight
          'deadline_iso': null,
        },
        submitExtracted: (args) async => throw StateError('should never be called'),
        submitCloud: (text, {required onDeviceAttempted, onDeviceFailureReason}) async {
          capturedText = text;
          capturedAttempted = onDeviceAttempted;
          capturedReason = onDeviceFailureReason;
          return _fakeResult();
        },
      );

      expect(capturedText, 'finish the report');
      expect(capturedAttempted, isTrue);
      expect(capturedReason, contains('estimated_hours'));
      expect(result.domain, 'tasks');
    });

    test('falls back to cloud, honestly reasoned, when the on-device call itself throws', () async {
      String? capturedReason;

      final result = await routeQuickCapture(
        'finish the report',
        onDeviceExtract: (_) async => throw Exception('model failed to load'),
        submitExtracted: (args) async => throw StateError('should never be called'),
        submitCloud: (text, {required onDeviceAttempted, onDeviceFailureReason}) async {
          capturedReason = onDeviceFailureReason;
          return _fakeResult();
        },
      );

      expect(capturedReason, contains('model failed to load'));
      expect(result.domain, 'tasks');
    });

    test('a genuine failure from the cloud fallback itself also propagates', () async {
      expect(
        () => routeQuickCapture(
          'finish the report',
          onDeviceExtract: (_) async => throw Exception('model failed to load'),
          submitExtracted: (args) async => throw StateError('should never be called'),
          submitCloud: (_, {required onDeviceAttempted, onDeviceFailureReason}) async => throw Exception('real cloud failure'),
        ),
        throwsA(isA<Exception>()),
      );
    });
  });
}
