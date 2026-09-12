/// The real, live `GET /health` implementation -- the real connectivity
/// signal `features/outage/outage_detector.dart`'s own top-of-file
/// comment names as "genuinely deferred... an actual network health-check
/// call," closed here.
///
/// A REAL, DELIBERATE DESIGN CHOICE: this is a dedicated, periodic
/// health-check against the one real, unauthenticated, side-effect-free
/// endpoint this backend has always exposed for exactly this purpose
/// (`GET /health`, confirmed live and unauthenticated before writing
/// this file) -- NOT a hook into every existing real fetcher's own
/// success/failure. Threading outage detection through every real
/// fetcher in this app (`fetchToday`, `captureTask`, all the rest) would
/// mean touching every one of them for a genuinely orthogonal concern;
/// a single, dedicated, low-cost poll is the same real "one shared
/// concern, one real owner" discipline this project already applies
/// elsewhere (`core/gemini_quota.py`'s own single reservation point on
/// the backend side, a different concern but the identical shape of
/// choice).
///
/// REAL, DELIBERATE: this call NEVER throws. A genuine network failure,
/// a non-200 response, a timeout -- all of it collapses to a plain
/// `false`, matching `outage_detector.dart`'s own real
/// `recordFailure()`/`recordSuccess()` contract, which take a real
/// success/failure fact, never an exception to unwrap. A background
/// health-check that itself threw would be a real, new, undisclosed
/// crash surface for a feature that exists specifically to degrade
/// gracefully.
library;

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/config/api_config.dart';

typedef HealthCheckCall = Future<bool> Function();

HealthCheckCall createHealthCheckCall({
  required http.Client client,
  String baseUrl = ApiConfig.baseUrl,
  Duration timeout = const Duration(seconds: 10),
}) {
  return () async {
    try {
      final response = await client.get(Uri.parse('$baseUrl/health')).timeout(timeout);
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  };
}
