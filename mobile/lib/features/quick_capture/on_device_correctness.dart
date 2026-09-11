// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Zero Flutter dependencies, same testability tier as
// `in_motion_logic.dart`/`computed_state.dart` -- `dart test` is the real
// verification.
//
// `QUORUM_FINAL_COMPLETION_PLAN.md` Session 8's own real, structural
// correctness bar: "not simply 'did it produce valid JSON,' but a real,
// structural sanity check per domain -- e.g., a parsed date that's
// genuinely in the future, an amount that's genuinely a positive real
// number." This file is the real, disclosed, hand-verified-parity port of
// the SAME structural checks `backend/src/quorum_backend/features/
// retry_queue_drainer.py`'s own `validate_and_build_task_proposal()`/
// `validate_and_build_finance_proposal()` and `quick_capture.py`'s own
// `validate_and_build_calendar_proposal()` already enforce server-side --
// read directly from that real, current code before writing this file,
// not guessed or invented fresh. The numeric bounds below
// (`_maxEstimatedHours`, `_maxFinanceAmount`, `_maxTaskTitleLength`) are
// copied verbatim from that module's own real constants.
//
// RESOLVED, a real, disclosed standard-tier review finding (PR #84):
// this file's own calendar checks were initially missing the real
// `_MAX_EVENT_DURATION_HOURS`/`_MAX_CALENDAR_TITLE_LENGTH`/invitee-email-
// format checks `validate_and_build_calendar_proposal()` already
// enforces, and no domain here checked `operation` against the real,
// closed set `capture_action_from_extracted_args()`'s own dispatch
// actually supports (calendar/email always "create", career always
// "update") -- found by direct comparison against that live dispatch
// function, not assumed correct from this file's own prior comment.
// Fixed: all four gaps closed below. One real, deliberate, remaining
// asymmetry, not a gap: `update`/`delete` reference-based operations
// (tasks/finance) only check that `reference_description` is a real,
// non-empty string, never attempting to replicate the backend's own
// `_resolve_single_reference()` matching -- that function needs this
// exact user's own live database rows, which this client-side bar
// structurally cannot see before submitting, so a real match/no-match
// decision is correctly left to the real backend either way.
//
// A REAL, DELIBERATE SAFETY FACT, stated plainly rather than assumed:
// passing this check is a real, honest PREDICTION that the real backend
// validator will also accept the same args -- it is never itself a
// security or correctness boundary. `POST /quick_capture/extracted`'s own
// docstring already establishes that the backend re-validates every one
// of these fields from scratch regardless of what this function decides.
// A false positive here (this function says "trust it," the backend then
// rejects it anyway) produces an honest, if slightly wasted, real `502`
// -- never a wrong action. A false negative (this function says "don't
// trust it" for an input the backend would actually have accepted) only
// ever costs one extra, real cloud round trip. Both failure directions
// are real, but neither is unsafe -- this is a routing optimization, not
// a second Gate.

/// The real, closed set of domains `build_extraction_prompt()` (backend)
/// ever asks for -- mirrored here so an on-device result naming anything
/// else is rejected immediately, before any per-field check runs.
const _realDomains = {'tasks', 'finance', 'calendar', 'career', 'email'};

/// Verbatim from `retry_queue_drainer.py`'s own real constants.
const double _maxEstimatedHours = 999.9;
const double _maxFinanceAmount = 99999999.99;
const int _maxTaskTitleLength = 500;
const int _maxFinanceCategoryLength = 200;
const int _maxFinancePayeeLength = 200;

/// Verbatim from `quick_capture.py`'s own real calendar constants.
const int _maxCalendarTitleLength = 500;
const double _maxEventDurationHours = 24.0;

/// Real result of a real structural check -- [passed] decides whether the
/// caller should trust the on-device extraction; [reason] is always a
/// real, short, human-readable string when [passed] is `false`, used only
/// for this session's own "every fallback is logged, not silent"
/// requirement (`POST /quick_capture`'s new `on_device_failure_reason`
/// field) -- never shown to the user directly.
class OnDeviceCorrectnessResult {
  final bool passed;
  final String? reason;

  const OnDeviceCorrectnessResult.pass() : passed = true, reason = null;
  const OnDeviceCorrectnessResult.fail(this.reason) : passed = false;
}

/// The real, single entry point -- given a real, on-device-produced
/// extraction map (matching `_QUICK_CAPTURE_EXTRACTION_SCHEMA`'s own real
/// 17-field shape field-for-field), decides whether it passes this
/// session's own real correctness bar. Never throws -- a genuinely
/// malformed `args` (missing keys, wrong types) is itself a real, honest
/// failure of the bar, not a bug in this function.
OnDeviceCorrectnessResult checkOnDeviceExtraction(Map<String, dynamic> args) {
  final domain = args['domain'];
  if (domain is! String || !_realDomains.contains(domain)) {
    return OnDeviceCorrectnessResult.fail('unrecognized or missing domain: $domain');
  }

  switch (domain) {
    case 'tasks':
      return _checkTasks(args);
    case 'finance':
      return _checkFinance(args);
    case 'calendar':
      return _checkCalendar(args);
    case 'career':
      return _checkCareer(args);
    case 'email':
      return _checkEmail(args);
    default:
      // Unreachable -- `_realDomains.contains(domain)` above already
      // narrowed this. Kept for the analyzer's own exhaustiveness sake,
      // matching `_modelIdToString`'s own established pattern.
      return const OnDeviceCorrectnessResult.fail('unreachable domain branch');
  }
}

OnDeviceCorrectnessResult _checkTasks(Map<String, dynamic> args) {
  final operation = args['operation'];
  if (operation == 'update' || operation == 'delete') {
    return _checkNonEmptyString(args['reference_description'], 'reference_description');
  }
  if (operation != 'create') {
    return OnDeviceCorrectnessResult.fail('unrecognized tasks operation: $operation');
  }

  final title = args['title'];
  if (title is! String || title.trim().isEmpty) {
    return const OnDeviceCorrectnessResult.fail('title is missing or empty');
  }
  if (title.length > _maxTaskTitleLength) {
    return const OnDeviceCorrectnessResult.fail('title exceeds $_maxTaskTitleLength characters');
  }

  // REAL, DISCLOSED PARITY WITH A REAL, ON-DEVICE-FOUND BUG THIS SAME
  // NIGHT (`retry_queue_drainer.py`'s own real fix, tonight): a real,
  // ordinary duration-less phrasing ("finish report by tomorrow")
  // honestly returns `estimated_hours: null` -- the backend now
  // correctly REJECTS that with a clean error rather than crashing, so
  // this bar must treat it as a real correctness-bar failure too, not
  // a nullable field it can safely skip.
  final rawHours = args['estimated_hours'];
  if (rawHours is! num) {
    return const OnDeviceCorrectnessResult.fail('estimated_hours is missing or not a real number');
  }
  final hours = rawHours.toDouble();
  if (!hours.isFinite || hours <= 0) {
    return OnDeviceCorrectnessResult.fail('estimated_hours is not a real, finite, positive number: $hours');
  }
  if (hours > _maxEstimatedHours) {
    return const OnDeviceCorrectnessResult.fail('estimated_hours exceeds $_maxEstimatedHours');
  }

  final deadlineIso = args['deadline_iso'];
  if (deadlineIso != null) {
    if (deadlineIso is! String || DateTime.tryParse(deadlineIso) == null) {
      return OnDeviceCorrectnessResult.fail('deadline_iso does not parse as a real date: $deadlineIso');
    }
  }

  return const OnDeviceCorrectnessResult.pass();
}

OnDeviceCorrectnessResult _checkFinance(Map<String, dynamic> args) {
  final action = args['action'];
  if (action == 'update_expense' || action == 'delete_expense') {
    return _checkNonEmptyString(args['reference_description'], 'reference_description');
  }
  if (action != 'log_expense' && action != 'update_budget') {
    return OnDeviceCorrectnessResult.fail('unrecognized finance action: $action');
  }

  final rawAmount = args['amount'];
  if (rawAmount is! num) {
    return const OnDeviceCorrectnessResult.fail('amount is missing or not a real number');
  }
  final amount = rawAmount.toDouble();
  if (!amount.isFinite || amount <= 0) {
    return OnDeviceCorrectnessResult.fail('amount is not a real, finite, positive number: $amount');
  }
  if (amount > _maxFinanceAmount) {
    return const OnDeviceCorrectnessResult.fail('amount exceeds $_maxFinanceAmount');
  }

  final category = args['category'];
  if (category is! String || category.trim().isEmpty) {
    return const OnDeviceCorrectnessResult.fail('category is missing or empty');
  }
  if (category.length > _maxFinanceCategoryLength) {
    return const OnDeviceCorrectnessResult.fail('category exceeds $_maxFinanceCategoryLength characters');
  }

  final payee = args['payee'];
  if (payee != null) {
    if (payee is! String || payee.trim().isEmpty) {
      return const OnDeviceCorrectnessResult.fail('payee is present but not a real, non-empty string');
    }
    if (payee.length > _maxFinancePayeeLength) {
      return const OnDeviceCorrectnessResult.fail('payee exceeds $_maxFinancePayeeLength characters');
    }
  }

  return const OnDeviceCorrectnessResult.pass();
}

OnDeviceCorrectnessResult _checkCalendar(Map<String, dynamic> args) {
  // Mirrors the real dispatch: `domain == "calendar"` is only ever
  // supported with `operation == "create"` -- editing or cancelling an
  // existing calendar event is not supported.
  if (args['operation'] != 'create') {
    return OnDeviceCorrectnessResult.fail('unrecognized calendar operation: ${args['operation']}');
  }
  final title = args['title'];
  if (title is! String || title.trim().isEmpty) {
    return const OnDeviceCorrectnessResult.fail('title is missing or empty');
  }
  if (title.length > _maxCalendarTitleLength) {
    return const OnDeviceCorrectnessResult.fail('title exceeds $_maxCalendarTitleLength characters');
  }

  final startIso = args['start_iso'];
  final endIso = args['end_iso'];
  if (startIso is! String || endIso is! String) {
    return const OnDeviceCorrectnessResult.fail('start_iso/end_iso are missing or not real strings');
  }
  final start = DateTime.tryParse(startIso);
  final end = DateTime.tryParse(endIso);
  if (start == null || end == null) {
    return OnDeviceCorrectnessResult.fail('start_iso/end_iso do not parse as real dates: $startIso / $endIso');
  }
  // A real, deliberate on-device-side mirror of the backend's own
  // timezone-aware requirement (`validate_and_build_calendar_proposal`) --
  // `DateTime.tryParse` on a string with no UTC/offset marker produces a
  // real, local-only `DateTime` (`isUtc == false` and no offset was ever
  // stated in the text), which the backend correctly rejects as
  // genuinely ambiguous.
  if (!startIso.contains('Z') && !_hasExplicitOffset(startIso)) {
    return OnDeviceCorrectnessResult.fail('start_iso has no real, explicit timezone: $startIso');
  }
  if (!endIso.contains('Z') && !_hasExplicitOffset(endIso)) {
    return OnDeviceCorrectnessResult.fail('end_iso has no real, explicit timezone: $endIso');
  }
  if (!end.isAfter(start)) {
    return OnDeviceCorrectnessResult.fail('end ($end) is not after start ($start)');
  }
  // A real, genuinely-in-the-future check, matching this session's own
  // spec text example verbatim ("a parsed date that's genuinely in the
  // future") -- a real calendar event proposed for a moment that has
  // already passed is a strong, cheap signal the on-device extraction
  // misread a relative date phrase ("next Tuesday").
  if (!start.isAfter(DateTime.now())) {
    return OnDeviceCorrectnessResult.fail('start ($start) is not genuinely in the future');
  }
  if (end.difference(start).inSeconds > _maxEventDurationHours * 3600) {
    return OnDeviceCorrectnessResult.fail('event spans ${end.difference(start)}, exceeding $_maxEventDurationHours hours');
  }

  final inviteeEmail = args['invitee_email'];
  if (inviteeEmail != null) {
    if (inviteeEmail is! String || !_looksLikeARealEmail(inviteeEmail)) {
      return OnDeviceCorrectnessResult.fail('invitee_email is present but not a real, plausible email address: $inviteeEmail');
    }
  }

  return const OnDeviceCorrectnessResult.pass();
}

/// A real, deliberately minimal port of `_looks_like_a_real_email()`
/// (`quick_capture.py`) -- same real shape requirement (`local@domain.tld`),
/// same reasoning for staying simple rather than a full RFC 5322 regex.
bool _looksLikeARealEmail(String value) {
  if (value.isEmpty || value.contains(RegExp(r'\s'))) return false;
  final atIndex = value.lastIndexOf('@');
  if (atIndex <= 0 || atIndex == value.length - 1) return false;
  final domain = value.substring(atIndex + 1);
  return domain.contains('.') && !domain.startsWith('.') && !domain.endsWith('.');
}

bool _hasExplicitOffset(String iso) {
  // A real ISO 8601 offset is `+HH:MM`/`-HH:MM` after the time portion --
  // checked past index 10 (`YYYY-MM-DD`) so the leading `-` in the date
  // itself is never mistaken for a negative offset.
  final tail = iso.length > 10 ? iso.substring(10) : '';
  return tail.contains('+') || tail.contains('-');
}

OnDeviceCorrectnessResult _checkCareer(Map<String, dynamic> args) {
  // Mirrors `capture_action_from_extracted_args()`'s own real dispatch:
  // `domain == "career"` is only ever supported with `operation ==
  // "update"` -- Quorum never creates a new application from free text.
  if (args['operation'] != 'update') {
    return OnDeviceCorrectnessResult.fail('unrecognized career operation: ${args['operation']}');
  }
  final reference = _checkNonEmptyString(args['reference_description'], 'reference_description');
  if (!reference.passed) return reference;
  return _checkNonEmptyString(args['new_status'], 'new_status');
}

OnDeviceCorrectnessResult _checkEmail(Map<String, dynamic> args) {
  // Mirrors the real dispatch: `domain == "email"` is only ever
  // supported with `operation == "create"` -- editing or cancelling an
  // already-sent email is not supported.
  if (args['operation'] != 'create') {
    return OnDeviceCorrectnessResult.fail('unrecognized email operation: ${args['operation']}');
  }
  final recipientDescription = args['recipient_description'];
  final recipientEmail = args['recipient_email'];
  final hasRecipient = (recipientDescription is String && recipientDescription.trim().isNotEmpty) ||
      (recipientEmail is String && recipientEmail.trim().isNotEmpty);
  if (!hasRecipient) {
    return const OnDeviceCorrectnessResult.fail('neither recipient_description nor recipient_email is a real, non-empty string');
  }
  return _checkNonEmptyString(args['user_intent'], 'user_intent');
}

OnDeviceCorrectnessResult _checkNonEmptyString(dynamic value, String fieldName) {
  if (value is! String || value.trim().isEmpty) {
    return OnDeviceCorrectnessResult.fail('$fieldName is missing or empty');
  }
  return const OnDeviceCorrectnessResult.pass();
}
