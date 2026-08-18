// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Zero Flutter dependencies — plain Dart, `dart test` is
// the real verification.
//
// A small, shared utility factored out because more than one real screen
// this batch (MOBILE_05's Needs You Now, and potentially later gate/
// action-summary surfaces) needs to turn a raw backend `action_type`
// string into something a person can actually read — never raw jargon,
// never a crash on an unrecognized value. Every case below was
// cross-checked directly against the real, current `ActionType` enum in
// `backend/src/quorum_backend/gate/schemas.py` before being written, not
// assumed from memory.

/// Every real `ActionType` this project's backend currently defines
/// (11 values, confirmed live against `backend/src/quorum_backend/gate/
/// schemas.py` before writing this switch) gets a real, readable label.
/// An unrecognized type — a real possibility if the backend adds a new
/// `ActionType` before this file is updated — falls back to a de-snaked,
/// readable version instead of a crash or raw jargon.
String readableActionType(String actionType) {
  switch (actionType) {
    case 'send_email':
      return 'Send an email';
    case 'create_calendar_event_external':
      return 'Create a calendar invite';
    case 'create_calendar_event_local':
      return 'Add a calendar event';
    case 'create_task':
      return 'Create a task';
    case 'update_task':
      return 'Update a task';
    case 'log_expense':
      return 'Log an expense';
    case 'update_budget':
      return 'Update a budget';
    case 'create_note':
      return 'Create a note';
    case 'update_application_status':
      return 'Update an application';
    case 'archive_email':
      return 'Archive an email';
    case 'label_email':
      return 'Label an email';
    default:
      return _deSnake(actionType);
  }
}

/// 'update_application_status' -> 'Update Application Status'. Never
/// throws on an empty or malformed string — the honest fallback of a
/// fallback stays readable, never a crash.
String _deSnake(String raw) {
  if (raw.isEmpty) return 'Action';
  return raw
      .split('_')
      .where((word) => word.isNotEmpty)
      .map((word) => word[0].toUpperCase() + word.substring(1))
      .join(' ');
}
