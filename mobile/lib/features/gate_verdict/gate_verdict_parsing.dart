/// `DEC-214` (product rebuild Part C, Priority 1) -- the real,
/// deliberately Flutter-free half of the Gate-verdict parsing/
/// rendering split. Every structured-write API client
/// (`create_calendar_event_api.dart`/`create_task_api.dart`/
/// `update_budget_api.dart`/`create_application_api.dart`/
/// `schedule_interview_api.dart`/`create_expense_api.dart`) needs
/// [parseFindings]/[parseObjections], and this project's own
/// established convention keeps those API files `dart test`-runnable
/// with zero Flutter dependency (see `calendar_sync_test.dart`'s own
/// docstring for the precedent this follows). The real rendering --
/// `showGateVerdictSheet()`, which genuinely does need Flutter --
/// lives in the sibling `gate_verdict_card.dart` instead, which
/// imports this file, never the other way around.
///
/// Mirrors `quick_capture_api.dart`'s own already-established JSON
/// shape exactly -- a small, shared home for logic that was about to
/// be duplicated six times (one per structured-write result type)
/// rather than written once.
library;

import 'package:quorum_mobile/features/gate_reveal/gate_reveal_logic.dart';

List<FindingSummary> parseFindings(List<dynamic> json) {
  return [
    for (final raw in json)
      FindingSummary(
        validator: (raw as Map<String, dynamic>)['validator'] as String,
        claim: raw['claim'] as String,
        visualState: visualStateForEvidence(raw['evidence_state'] as String),
      ),
  ];
}

List<ObjectionSummary> parseObjections(List<dynamic> json) {
  return [
    for (final raw in json)
      ObjectionSummary(
        category: (raw as Map<String, dynamic>)['category'] as String,
        severity: raw['severity'] as String,
        description: raw['description'] as String,
        signedOff: raw['signed_off'] as bool,
      ),
  ];
}
