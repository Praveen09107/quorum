// Real deep links into Gmail/Calendar from a real execution artifact
// (`DEC-191`, product rebuild Block C).
//
// Zero Flutter dependency -- pure string construction, so the logic is
// testable without a widget harness. [launchArtifactLink] (the one
// function that actually needs `url_launcher`) lives in a separate,
// thin wrapper in the screen itself, matching this project's own
// established "pure logic file + a thin widget-layer caller" split.
//
// WHY THIS EXISTS: "it drafted this in my Gmail, let me go look at it"
// is the single most direct answer to the real complaint that started
// this whole rebuild -- a real artifact id with nowhere to tap is
// barely better than no artifact at all.
//
// AN HONEST CALIBRATION, stated plainly rather than overclaimed: the
// Calendar link (`html_link`) is NOT a guess -- it is the real,
// literal URL Google's own Calendar API returns on a successful
// booking (`action_executor.py::_real_google_calendar_post()`), used
// here verbatim. The Gmail link IS a constructed URL, built from the
// real `message_id` Gmail's own API returns, using the long-
// established `#all/<message_id>` web permalink pattern that many
// real third-party Gmail integrations rely on. That pattern was not
// independently re-verified in a live browser this session (no browser
// automation was available) -- it is a well-documented, standard
// Gmail web-client behavior, not a fabricated guess, but it is
// disclosed here as unverified-this-session rather than claimed as
// confirmed, matching this project's own standing honesty discipline.
// If it is ever found to be wrong, the fix is entirely contained to
// [gmailWebLink] below.

/// One real, openable link derived from an execution artifact.
class ArtifactLink {
  final String url;
  final String label;

  const ArtifactLink({required this.url, required this.label});
}

/// Builds the real Gmail web permalink for a message id.
///
/// Deliberately keyed on `message_id`, never `draft_id`, even when the
/// artifact came from a real `CREATE_EMAIL_DRAFT` -- Gmail's own
/// `drafts.create` response nests a real `message` object with its own
/// `id`, and Gmail's web client addresses a draft through that
/// underlying message id, not through the draft wrapper id. This means
/// one code path serves a drafted email and a sent email identically;
/// no draft-specific URL logic is needed at all.
String gmailWebLink(String messageId) => 'https://mail.google.com/mail/u/0/#all/$messageId';

/// Resolves the real artifact map into the one link worth showing, or
/// `null` when the artifact carries nothing this function recognizes
/// (an honest absence, never a broken link).
///
/// Calendar is checked first: `html_link` is a real, literal URL from
/// Google's own API, strictly more trustworthy than a constructed one,
/// so it is preferred whenever both are somehow present (never
/// expected in practice -- one real artifact is always either a Gmail
/// or a Calendar shape, never both).
ArtifactLink? artifactLinkFor(Map<String, dynamic>? artifact) {
  if (artifact == null) return null;

  final htmlLink = artifact['html_link'];
  if (htmlLink is String && htmlLink.isNotEmpty) {
    return ArtifactLink(url: htmlLink, label: 'Open in Calendar');
  }

  final messageId = artifact['message_id'];
  if (messageId is String && messageId.isNotEmpty) {
    final isDraft = artifact['draft_id'] is String && (artifact['draft_id'] as String).isNotEmpty;
    return ArtifactLink(url: gmailWebLink(messageId), label: isDraft ? 'Open draft in Gmail' : 'Open in Gmail');
  }

  return null;
}
