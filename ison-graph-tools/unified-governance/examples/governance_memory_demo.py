#!/usr/bin/env python3
"""
Governance Memory Integration Demo
==================================

Demonstrates agent-memory and ISONCache patterns integrated with
unified governance for:
- Compliance decision learning
- Pattern detection
- Cached context with token budgeting
- Session continuity
"""

import sys
sys.path.insert(0, "../src")

from unified_governance import (
    UnifiedGovernanceEngine,
    quick_unified_governance,
    RegulationJurisdiction,
)


def main():
    print("=" * 60)
    print("Governance Memory Integration Demo")
    print("=" * 60)

    # =========================================================================
    # 1. Initialize with Memory
    # =========================================================================
    print("\n1. INITIALIZATION WITH MEMORY")
    print("-" * 40)

    engine = quick_unified_governance("memory_demo", setup_defaults=True)
    print("Created UnifiedGovernanceEngine with:")
    print("  - GovernanceMemoryStore (decision memory)")
    print("  - CachedGovernanceContext (token-budgeted)")
    print("  - GovernanceSessionManager (session continuity)")

    # =========================================================================
    # 2. Add Governance Conventions
    # =========================================================================
    print("\n2. GOVERNANCE CONVENTIONS")
    print("-" * 40)

    # Add organizational conventions
    engine.add_governance_convention(
        category="pii_handling",
        rule="always_encrypt_ssn",
        description="SSN must always be encrypted at rest and in transit",
        regulations=["gdpr", "ccpa", "glba"],
    )
    print("Added convention: always_encrypt_ssn")

    engine.add_governance_convention(
        category="consent",
        rule="explicit_consent_for_marketing",
        description="Marketing communications require explicit opt-in consent",
        regulations=["gdpr", "ccpa"],
    )
    print("Added convention: explicit_consent_for_marketing")

    engine.add_governance_convention(
        category="data_sharing",
        rule="no_third_party_without_consent",
        description="Never share PII with third parties without explicit consent",
        regulations=["gdpr", "ccpa"],
    )
    print("Added convention: no_third_party_without_consent")

    # =========================================================================
    # 3. Add Warning Patterns
    # =========================================================================
    print("\n3. WARNING PATTERNS")
    print("-" * 40)

    # Add proactive warning patterns
    engine.add_warning_pattern(
        name="ssn_sharing_warning",
        trigger={
            "action": "share_with_third_party",
            "any_pii_type": "ssn",
        },
        warning_message="CRITICAL: Sharing SSN with third parties is high-risk",
        severity="critical",
        auto_block=False,
    )
    print("Added warning: ssn_sharing_warning")

    engine.add_warning_pattern(
        name="bulk_export_warning",
        trigger={
            "action": "transfer_data_external",
            "pii_types": ["email", "phone", "address"],
        },
        warning_message="Bulk PII export detected - verify authorization",
        severity="high",
    )
    print("Added warning: bulk_export_warning")

    # =========================================================================
    # 4. Start a Governance Session
    # =========================================================================
    print("\n4. SESSION MANAGEMENT")
    print("-" * 40)

    session_id = engine.start_session("Customer data migration compliance review")
    print(f"Started session: {session_id}")

    # =========================================================================
    # 5. Register Subjects and Agents
    # =========================================================================
    print("\n5. SETUP SUBJECTS AND AGENTS")
    print("-" * 40)

    engine.register_subject(
        subject_id="customer_001",
        email="alice@example.com",
        jurisdiction=RegulationJurisdiction.EU,
    )
    print("Registered: customer_001 (EU)")

    engine.register_subject(
        subject_id="customer_002",
        email="bob@example.com",
        jurisdiction=RegulationJurisdiction.US_CALIFORNIA,
    )
    print("Registered: customer_002 (California)")

    engine.grant_agent_pii_access(
        agent_id="migration_agent",
        pii_types=["email", "phone", "address"],
        purpose="data_migration",
        legal_basis="contract",
    )
    print("Granted migration_agent: email, phone, address access")

    # =========================================================================
    # 6. Perform Compliance Checks (Builds Decision Memory)
    # =========================================================================
    print("\n6. COMPLIANCE CHECKS (BUILDING MEMORY)")
    print("-" * 40)

    # Check 1: Permitted action
    print("\nCheck 1: migration_agent reading email...")
    result1 = engine.check_compliance(
        agent_id="migration_agent",
        action="read_personal_data",
        pii_types=["email"],
        data_subject_id="customer_001",
        context={
            "gdpr": {
                "has_consent": True,
                "has_legal_basis": True,
                "data_minimized": True,
                "retention_defined": True,
                "processing_purpose": "migration",
            },
        },
    )
    print(f"  Outcome: {'PERMITTED' if result1['permitted'] else 'BLOCKED'}")
    print(f"  Decision ID: {result1.get('decision_id')}")

    # Check 2: Another permitted action (same pattern)
    print("\nCheck 2: migration_agent reading phone...")
    result2 = engine.check_compliance(
        agent_id="migration_agent",
        action="read_personal_data",
        pii_types=["phone"],
        data_subject_id="customer_001",
        context={
            "gdpr": {
                "has_consent": True,
                "has_legal_basis": True,
                "data_minimized": True,
                "retention_defined": True,
                "processing_purpose": "migration",
            },
        },
    )
    print(f"  Outcome: {'PERMITTED' if result2['permitted'] else 'BLOCKED'}")

    # Check 3: Blocked action (no SSN access)
    print("\nCheck 3: migration_agent reading SSN (no access)...")
    result3 = engine.check_compliance(
        agent_id="migration_agent",
        action="read_personal_data",
        pii_types=["ssn"],
    )
    print(f"  Outcome: {'PERMITTED' if result3['permitted'] else 'BLOCKED'}")
    print(f"  Reason: {result3.get('blocking_issues', [{}])[0].get('issue', 'N/A')}")

    # Check 4: Third party sharing (triggers warning)
    print("\nCheck 4: migration_agent sharing with third party...")
    result4 = engine.check_compliance(
        agent_id="migration_agent",
        action="share_with_third_party",
        pii_types=["email", "phone"],
        context={
            "ccpa": {
                "has_notice": True,
                "opt_out_honored": True,
            },
        },
    )
    print(f"  Outcome: {'PERMITTED' if result4['permitted'] else 'BLOCKED'}")
    print(f"  Warnings: {len(result4.get('warnings', []))}")

    # =========================================================================
    # 7. Check for Warnings Before Action
    # =========================================================================
    print("\n7. PROACTIVE WARNINGS")
    print("-" * 40)

    # Check warnings for SSN sharing
    warnings = engine.check_warnings(
        agent_id="migration_agent",
        action="share_with_third_party",
        pii_types=["ssn"],
    )
    print(f"Warnings for sharing SSN with third party:")
    for w in warnings:
        print(f"  [{w.get('severity', 'medium').upper()}] {w.get('message')}")
        if w.get('learned'):
            print(f"    (Learned from {w.get('pattern_id')})")

    # =========================================================================
    # 8. Get Cached Context (Token-Budgeted)
    # =========================================================================
    print("\n8. CACHED GOVERNANCE CONTEXT")
    print("-" * 40)

    context = engine.get_context_for_action(
        agent_id="migration_agent",
        action="transfer_data_external",
        pii_types=["email", "phone"],
        token_budget=1500,
    )

    print(f"Context retrieved:")
    print(f"  Tokens used: {context['tokens_used']}/{context['token_budget']}")
    print(f"  Cache hit: {context['cache_hit']}")
    print(f"  Categories included: {context['categories_included']}")
    print(f"  Categories truncated: {context['categories_truncated']}")
    print(f"\nISON Output (first 500 chars):")
    print(context['ison_output'][:500] + "...")

    # =========================================================================
    # 9. Provide Feedback (Reinforcement Learning)
    # =========================================================================
    print("\n9. FEEDBACK AND LEARNING")
    print("-" * 40)

    # Provide feedback on a decision
    if result3.get('decision_id'):
        feedback = engine.provide_feedback(
            decision_id=result3['decision_id'],
            feedback="Correct - migration_agent should not have SSN access",
            was_correct=True,
        )
        print(f"Feedback recorded: {feedback}")

    # =========================================================================
    # 10. View Learned Patterns
    # =========================================================================
    print("\n10. LEARNED PATTERNS")
    print("-" * 40)

    patterns = engine.memory.get_patterns_for_action("read_personal_data")
    print(f"Patterns for 'read_personal_data': {len(patterns)}")
    for p in patterns:
        print(f"  - {p.get('name')}: confidence={p.get('confidence'):.2f}, "
              f"frequency={p.get('frequency')}")

    # =========================================================================
    # 11. End Session
    # =========================================================================
    print("\n11. END SESSION")
    print("-" * 40)

    session_result = engine.end_session(
        outcome="success",
        summary="Migration compliance review completed with 4 checks",
    )
    print(f"Session ended:")
    print(f"  Checks performed: {session_result['checks_count']}")
    print(f"  Decisions made: {session_result['decisions_count']}")
    print(f"  Open issues: {session_result['open_issues_count']}")

    # =========================================================================
    # 12. Session Handoff (Continuity)
    # =========================================================================
    print("\n12. SESSION HANDOFF")
    print("-" * 40)

    handoff = engine.get_session_handoff()
    print(f"Previous session: {handoff.get('previous_session')}")
    print(f"Previous task: {handoff.get('previous_task')}")
    print(f"Previous outcome: {handoff.get('previous_outcome')}")
    print(f"Open issues from previous: {len(handoff.get('open_issues', []))}")

    # =========================================================================
    # 13. Memory Statistics
    # =========================================================================
    print("\n13. MEMORY STATISTICS")
    print("-" * 40)

    mem_stats = engine.memory.get_stats()
    print(f"Decision memories: {mem_stats['total_decisions']}")
    print(f"Learned patterns: {mem_stats['total_patterns']}")
    print(f"  High confidence: {mem_stats['high_confidence_patterns']}")
    print(f"Conventions: {mem_stats['total_conventions']}")
    print(f"Warning patterns: {mem_stats['total_warning_patterns']}")
    print(f"Decisions by outcome: {mem_stats['decisions_by_outcome']}")

    session_stats = engine.sessions.get_stats()
    print(f"\nSession stats:")
    print(f"  Total sessions: {session_stats['total_sessions']}")
    print(f"  Total checks: {session_stats['total_checks']}")

    # =========================================================================
    # 14. Demonstrate Cache Efficiency
    # =========================================================================
    print("\n14. CACHE EFFICIENCY")
    print("-" * 40)

    # First call (cache miss)
    ctx1 = engine.get_context_for_action(
        agent_id="migration_agent",
        action="read_personal_data",
        pii_types=["email"],
        token_budget=1000,
    )
    print(f"First call - Cache hit: {ctx1['cache_hit']}")

    # Second call (cache hit)
    ctx2 = engine.get_context_for_action(
        agent_id="migration_agent",
        action="read_personal_data",
        pii_types=["email"],
        token_budget=1000,
    )
    print(f"Second call - Cache hit: {ctx2['cache_hit']}")

    # =========================================================================
    # Save
    # =========================================================================
    print("\n" + "=" * 60)
    engine.save("governance_memory_demo.json")
    print("Graph saved to governance_memory_demo.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
