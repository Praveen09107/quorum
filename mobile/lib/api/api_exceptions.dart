/// Real, typed API failures -- every real fetcher (`trust_digest_api.dart`
/// and, over time, every other domain's) throws this, never a bare
/// `Exception('...')`. `statusCode` is nullable and honest: `null` means
/// the request never got a real HTTP response at all (a network failure),
/// genuinely different from a real server response that happened to be an
/// error -- the same "don't collapse two different real facts into one"
/// discipline this project holds itself to everywhere else.
class ApiException implements Exception {
  final String message;
  final int? statusCode;

  const ApiException(this.message, {this.statusCode});

  /// The real, honest signal for "your login has expired or was
  /// revoked" -- a caller can check this specifically to prompt a
  /// real sign-in flow, distinct from every other failure mode.
  bool get isAuthFailure => statusCode == 401;

  @override
  String toString() => message;
}
