// Real tests for api/capture_stream_api.dart (`DEC-189` Block B). Zero
// Flutter dependency -- `package:http`'s `MockClient.streaming`, which
// genuinely delivers a chunked response rather than one buffered body,
// so these tests exercise the real incremental-delivery code path this
// client exists for -- not just its final result.

import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/api/capture_stream_api.dart';

http.StreamedResponse _streamed(int status, Stream<String> chunks, {Map<String, String>? headers}) {
  return http.StreamedResponse(
    chunks.map(utf8.encode),
    status,
    headers: headers ?? {'content-type': 'text/event-stream'},
  );
}

Stream<String> _delayedChunks(List<String> chunks) async* {
  for (final chunk in chunks) {
    // A real microtask gap between chunks -- proves the fetcher is
    // genuinely consuming incrementally rather than only working
    // because everything happened to arrive synchronously.
    await Future<void>.delayed(Duration.zero);
    yield chunk;
  }
}

void main() {
  group('createCaptureStreamFetcher', () {
    test('throws a real 401 before ever sending a request when the token is null', () async {
      final fetcher = createCaptureStreamFetcher(
        getAccessToken: () async => null,
        client: MockClient.streaming((request, body) async => fail('must not reach the network')),
      );

      await expectLater(
        fetcher('anything').toList(),
        throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', 401)),
      );
    });

    test('surfaces a real non-200 status as an ApiException before yielding any event', () async {
      final fetcher = createCaptureStreamFetcher(
        getAccessToken: () async => 'tok',
        client: MockClient.streaming(
          (request, body) async => _streamed(503, Stream.value('{"detail":"Quick capture is not currently available."}')),
        ),
      );

      await expectLater(
        fetcher('anything').toList(),
        throwsA(isA<ApiException>()
            .having((e) => e.statusCode, 'statusCode', 503)
            .having((e) => e.message, 'message', contains('not currently available'))),
      );
    });

    test('yields real events incrementally as chunks arrive, across a split frame', () async {
      final chunks = [
        'data: {"event":"understanding.start","at_ms":0}\n\n',
        'data: {"event":"stage_a.chec', // deliberately split mid-frame
        'k","at_ms":5,"validator":"a","evidence_state":"verified_true"}\n\n',
        'data: {"event":"done","at_ms":10,"decision":"approve"}\n\n',
      ];

      final fetcher = createCaptureStreamFetcher(
        getAccessToken: () async => 'tok',
        client: MockClient.streaming((request, body) async => _streamed(200, _delayedChunks(chunks))),
      );

      final events = await fetcher('do the thing').toList();

      expect(events.map((e) => e.name), ['understanding.start', 'stage_a.check', 'done']);
      expect(events[1].data['validator'], 'a');
    });

    test('sends the real text and the real Authorization header', () async {
      http.BaseRequest? captured;
      Uint8List? capturedBody;

      final fetcher = createCaptureStreamFetcher(
        getAccessToken: () async => 'real-token',
        client: MockClient.streaming((request, bodyStream) async {
          captured = request;
          capturedBody = await bodyStream.toBytes();
          return http.StreamedResponse(Stream.value(utf8.encode('data: {"event":"done"}\n\n')), 200);
        }),
      );

      await fetcher('hello world').toList();

      expect(captured, isNotNull);
      expect(captured!.headers['Authorization'], 'Bearer real-token');
      final sentBody = jsonDecode(utf8.decode(capturedBody!)) as Map<String, dynamic>;
      expect(sentBody['text'], 'hello world');
      expect(sentBody['on_device_attempted'], false);
    });

    test('a genuinely malformed frame is skipped rather than aborting the whole stream', () async {
      final chunks = [
        'data: not valid json at all\n\n',
        'data: {"event":"done","at_ms":1}\n\n',
      ];
      final fetcher = createCaptureStreamFetcher(
        getAccessToken: () async => 'tok',
        client: MockClient.streaming((request, body) async => _streamed(200, Stream.fromIterable(chunks))),
      );

      final events = await fetcher('anything').toList();

      // The malformed frame produced no event, but the stream continued
      // and the real `done` event still arrived.
      expect(events.map((e) => e.name), ['done']);
    });

    test('a network failure before any response is a real honest ApiException', () async {
      final fetcher = createCaptureStreamFetcher(
        getAccessToken: () async => 'tok',
        client: MockClient.streaming((request, body) async => throw Exception('socket closed')),
      );

      await expectLater(
        fetcher('anything').toList(),
        throwsA(isA<ApiException>().having((e) => e.message, 'message', contains('check your connection'))),
      );
    });
  });
}
