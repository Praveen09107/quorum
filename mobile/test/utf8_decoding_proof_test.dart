// A real, empirical pin-down of package:http's actual content-type ->
// encoding behavior, kept as a permanent regression test.
//
// WHY THIS FILE EXISTS, honestly: while building `api/search_api.dart`
// (Roadmap Phase 4a), a test carrying real non-ASCII content ("—",
// "₹") failed, and the first hypothesis was a real, serious production
// bug -- that every one of this codebase's eight `api/*.dart` files
// silently mojibake'd non-ASCII text, since all of them use
// `response.body` and this project's real FastAPI backend sends
// `content-type: application/json` with NO charset parameter
// (confirmed live via a real curl against the real Cloud Run URL), and
// package:http's own `encodingForCharset` documents a latin1 fallback.
//
// That hypothesis was WRONG, and testing it rather than acting on it
// is what caught that. package:http 1.6.0's real `_encodingForHeaders`
// special-cases JSON: `application/json` with no charset resolves to
// utf8 (per RFC 3629), and only *other* media types fall back to
// latin1 (per RFC 2616). So `response.body` has always been correct
// for this backend, and no production fix was needed anywhere.
//
// The real, actual cause of the original failing test was in the test
// itself: `http.Response(String, 200)` with no headers at all gets
// `application/octet-stream`, hence latin1, and encoding "—" into
// latin1 genuinely throws. Fixed by having those MockClient responses
// send the same `application/json` header the real backend sends --
// which makes them more faithful to reality, not less.
//
// These two tests pin both halves of that real behavior down, so a
// future package:http upgrade that changed it would fail loudly here
// rather than silently corrupting real user-facing text.

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:test/test.dart';

void main() {
  test('application/json with no charset genuinely decodes as utf8 -- what the real backend sends', () {
    final realUtf8Bytes = utf8.encode('Spotify — ₹199.00');
    final response = http.Response.bytes(realUtf8Bytes, 200, headers: {'content-type': 'application/json'});

    expect(response.body, 'Spotify — ₹199.00');
  });

  test('a non-JSON content-type with no charset genuinely falls back to latin1 -- the real contrast', () {
    final realUtf8Bytes = utf8.encode('Spotify — ₹199.00');
    final response = http.Response.bytes(realUtf8Bytes, 200, headers: {'content-type': 'text/plain'});

    // Real mojibake, and a real, silent one -- no crash. This is the
    // case every api/*.dart file would genuinely be broken by if this
    // backend ever stopped sending application/json.
    expect(response.body, isNot('Spotify — ₹199.00'));
  });
}
