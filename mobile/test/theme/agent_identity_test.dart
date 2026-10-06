// Real tests for the `DEC-189` agent identity table.
//
// These are pure-Dart tests with no Flutter widget dependency beyond
// the `material` import the identity table itself needs for `Color`
// and `IconData`, so they run under both `dart test` and
// `flutter test`.

import 'package:flutter_test/flutter_test.dart';
import 'package:quorum_mobile/theme/agent_identity.dart';

void main() {
  group('kAgentIdentities', () {
    test('is exhaustive over QuorumAgent, so identityOf can never fail', () {
      for (final agent in QuorumAgent.values) {
        expect(kAgentIdentities.containsKey(agent), isTrue, reason: 'missing identity for $agent');
        // identityOf uses a non-null assertion on exactly this
        // invariant -- if the table is ever not exhaustive, this is
        // where it must break, not at runtime on a user's screen.
        expect(() => identityOf(agent), returnsNormally);
      }
    });

    test('every agent has a genuinely distinct accent color', () {
      final accents = kAgentIdentities.values.map((i) => i.accent.toARGB32()).toSet();
      expect(accents.length, kAgentIdentities.length,
          reason: 'two agents share an accent, making them indistinguishable');
    });

    test('every agent has a genuinely distinct icon', () {
      // The real accessibility requirement carried forward from ADD
      // §12.4: color must never be the only carrier of meaning, so two
      // agents sharing an icon would leave color doing the work alone
      // for anyone who cannot distinguish the two hues.
      final icons = kAgentIdentities.values.map((i) => i.icon.codePoint).toSet();
      expect(icons.length, kAgentIdentities.length, reason: 'two agents share an icon');
    });

    test('every agent has a real, non-empty name, domain and purpose', () {
      for (final identity in kAgentIdentities.values) {
        expect(identity.name.trim(), isNotEmpty);
        expect(identity.domain.trim(), isNotEmpty);
        expect(identity.purpose.trim(), isNotEmpty);
        // The purpose line is rendered to a real user and must be a
        // sentence, not a placeholder label.
        expect(identity.purpose.endsWith('.'), isTrue, reason: '${identity.name} purpose is not a sentence');
      }
    });

    test('domains are lowercase, matching the real backend strings', () {
      // agentForDomain lowercases its input before comparing, so a
      // capitalized domain in this table would be permanently
      // unmatchable.
      for (final identity in kAgentIdentities.values) {
        expect(identity.domain, identity.domain.toLowerCase());
      }
    });
  });

  group('agentForDomain', () {
    test('maps every real backend domain string to its agent', () {
      expect(agentForDomain('email'), QuorumAgent.email);
      expect(agentForDomain('calendar'), QuorumAgent.calendar);
      expect(agentForDomain('tasks'), QuorumAgent.tasks);
      expect(agentForDomain('finance'), QuorumAgent.finance);
      expect(agentForDomain('career'), QuorumAgent.career);
    });

    test('is case-insensitive and tolerates surrounding whitespace', () {
      // These strings arrive over HTTP from several real producers;
      // being strict about casing here would mean a correct response
      // rendering as an unknown agent.
      expect(agentForDomain('Email'), QuorumAgent.email);
      expect(agentForDomain('  CAREER '), QuorumAgent.career);
    });

    test('returns null rather than guessing for an unknown domain', () {
      // The real honesty requirement: defaulting an unrecognized
      // domain to some agent would show a user a confident, wrong
      // attribution. Null is the caller's signal to render an honest
      // unknown state.
      expect(agentForDomain('not_a_real_domain'), isNull);
      expect(agentForDomain(''), isNull);
      expect(agentForDomain('   '), isNull);
      expect(agentForDomain(null), isNull);
    });
  });

  group('kDomainAgents', () {
    test('contains the five real domain agents and never the Gate', () {
      // The Gate is the verification authority over the five, not a
      // sixth peer -- it has its own tab and must never appear in a
      // list of domain agents.
      expect(kDomainAgents.length, 5);
      expect(kDomainAgents.contains(QuorumAgent.gate), isFalse);
      expect(kDomainAgents.toSet().length, 5, reason: 'duplicate entry');
    });

    test('together with the Gate it covers every QuorumAgent value', () {
      final covered = {...kDomainAgents, QuorumAgent.gate};
      expect(covered, QuorumAgent.values.toSet());
    });
  });
}
