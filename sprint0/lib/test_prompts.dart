/// The fixed, real test set -- six prompts covering Tier-1's actual job
/// (expense extraction, task extraction, note extraction, single- and
/// multi-domain routing-signal classification, privacy classification),
/// each with an exact expected output shape so validity is mechanically
/// checkable, never a judgment call. Verbatim from IMPL_00's own spec.

class TestPrompt {
  final String id;
  final String input;
  final List<String> requiredFields;
  final Map<String, Type> fieldTypes;

  const TestPrompt({
    required this.id,
    required this.input,
    required this.requiredFields,
    required this.fieldTypes,
  });
}

final List<TestPrompt> sprint0TestPrompts = [
  TestPrompt(
    id: 'expense_extraction',
    input: 'spent 450 on groceries at DMart today',
    requiredFields: const ['amount', 'category', 'merchant', 'type'],
    fieldTypes: const {'amount': double, 'category': String, 'merchant': String, 'type': String},
  ),
  TestPrompt(
    id: 'task_extraction',
    input: 'remind me to submit the assignment by Friday',
    requiredFields: const ['title', 'deadline', 'type'],
    fieldTypes: const {'title': String, 'deadline': String, 'type': String},
  ),
  TestPrompt(
    id: 'note_extraction',
    input: 'meeting notes: discussed Q3 budget, need to follow up with finance team',
    requiredFields: const ['content', 'type'],
    fieldTypes: const {'content': String, 'type': String},
  ),
  TestPrompt(
    id: 'routing_single_domain',
    input: 'Can we move our 3pm to Thursday instead?',
    requiredFields: const ['domains', 'complexity', 'ambiguity'],
    fieldTypes: const {'domains': List, 'complexity': String, 'ambiguity': bool},
  ),
  TestPrompt(
    id: 'routing_multi_domain',
    input: "I need to pay the 2000 rupee conference fee but I'm not sure I "
        "can make it given my exam Friday",
    requiredFields: const ['domains', 'complexity'],
    fieldTypes: const {'domains': List, 'complexity': String},
  ),
  TestPrompt(
    id: 'privacy_classification',
    input: "here's my card number 4111-1111-1111-1111 for the subscription",
    requiredFields: const ['sensitivity', 'category'],
    fieldTypes: const {'sensitivity': String, 'category': String},
  ),
];

/// The real system prompt every test prompt is run with -- instructs the
/// model to respond with ONLY a raw JSON object matching the fields the
/// scenario names, nothing else. Real, necessary context: without this,
/// a real small on-device model has no idea what shape of output is
/// expected, and scoring would be measuring prompt-engineering quality,
/// not the model's own real structured-output capability.
String systemPromptFor(TestPrompt prompt) {
  final fields = prompt.requiredFields.join(', ');
  return 'You are a data-extraction engine. Respond with ONLY a single raw '
      'JSON object (no markdown fences, no prose) containing exactly these '
      'fields: $fields. Nothing else.';
}
