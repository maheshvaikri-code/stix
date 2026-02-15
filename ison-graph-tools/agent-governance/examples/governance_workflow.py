#!/usr/bin/env python3
"""
Agent Governance Workflow Example
=================================

This example demonstrates how to set up and use the comprehensive
governance system for AI agents.
"""

import tempfile
import os

from agent_governance import (
    GovernanceEngine,
    quick_governance,
    AuthorityLevel,
    RiskLevel,
    IncidentSeverity,
    EscalationLevel,
    ValuePriority,
    CapabilityMaturity,
)


def example_basic_setup():
    """
    Example: Basic governance setup and action checks
    """
    print("\n" + "="*60)
    print("BASIC GOVERNANCE SETUP")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Quick setup with defaults
        engine = quick_governance("my-agent-system", setup_defaults=True)

        print(f"\nCreated governance context: {engine.name}")

        # Register agents
        print("\n--- Registering Agents ---")
        engine.register_agent("agent_1", "Research Agent", AuthorityLevel.LIMITED)
        engine.register_agent("agent_2", "Writer Agent", AuthorityLevel.DELEGATED)

        # Register human overseer
        engine.register_human("human_1", "Admin Sarah", AuthorityLevel.ELEVATED, expertise=["general"])

        print("Registered: Research Agent (limited), Writer Agent (delegated)")
        print("Registered: Admin Sarah (elevated, human overseer)")

        # Grant some authority
        print("\n--- Granting Authority ---")
        engine.authority.grant_authority("agent_1", "read_public", "public_read_only")
        engine.authority.grant_authority("agent_2", "write_internal", "internal_only")
        print("agent_1: granted read_public")
        print("agent_2: granted write_internal")

        # Check actions
        print("\n--- Checking Actions ---")

        result1 = engine.check_action("agent_1", "read_public", {"data": "public_info"})
        print(f"agent_1 read_public: {'PERMITTED' if result1['permitted'] else 'DENIED'}")

        result2 = engine.check_action("agent_1", "write_external", {"destination": "api"})
        print(f"agent_1 write_external: {'PERMITTED' if result2['permitted'] else 'DENIED'}")
        if not result2["permitted"]:
            print(f"  Reason: {result2['reason']}")

        result3 = engine.check_action("agent_2", "write_internal", {"target": "database"})
        print(f"agent_2 write_internal: {'PERMITTED' if result3['permitted'] else 'DENIED'}")

        # Show stats
        print("\n--- Governance Stats ---")
        stats = engine.get_stats()
        print(f"Principals: {stats['authority']['principals']}")
        print(f"Decisions recorded: {stats['audit']['decisions']}")

        return engine


def example_policy_enforcement():
    """
    Example: Policy creation and enforcement
    """
    print("\n" + "="*60)
    print("POLICY ENFORCEMENT")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        engine = quick_governance("policy-demo", setup_defaults=False)

        # Create policies
        print("\n--- Creating Policies ---")

        # Data classification policy
        engine.add_policy("data_classification", [
            {
                "condition": "data_classification == 'secret'",
                "action": "deny_external",
                "description": "Secret data cannot leave"
            },
            {
                "condition": "data_classification == 'internal'",
                "action": "allow_internal",
                "description": "Internal data for internal use"
            }
        ], priority=100)

        # Safety policy
        engine.add_policy("safety", [
            {
                "condition": "safety_score < 0.5",
                "action": "deny",
                "description": "Block unsafe actions"
            },
            {
                "condition": "confidence < 0.7",
                "action": "escalate",
                "description": "Escalate low confidence"
            }
        ], priority=90)

        print("Created: data_classification (priority 100)")
        print("Created: safety (priority 90)")

        # Evaluate policies
        print("\n--- Evaluating Policies ---")

        result1 = engine.policy.evaluate({"data_classification": "secret"})
        print(f"Secret data: {result1['result']}")
        print(f"  Explanation: {result1['explanation']}")

        result2 = engine.policy.evaluate({"data_classification": "internal"})
        print(f"Internal data: {result2['result']}")

        result3 = engine.policy.evaluate({"safety_score": 0.3})
        print(f"Safety 0.3: {result3['result']}")

        result4 = engine.policy.evaluate({"confidence": 0.6})
        print(f"Confidence 0.6: {result4['result']}")

        return engine


def example_compliance_tracking():
    """
    Example: Compliance framework tracking
    """
    print("\n" + "="*60)
    print("COMPLIANCE TRACKING")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        engine = quick_governance("compliance-demo", setup_defaults=False)

        # Add EU AI Act framework
        print("\n--- Adding Compliance Framework ---")
        eu_ai_act = engine.compliance.add_framework(
            "EU AI Act",
            "EU",
            "2024-08-01",
            "high_risk_ai_systems",
            "European Union AI regulation"
        )

        # Add requirements
        req1 = engine.compliance.add_requirement(
            eu_ai_act,
            "Art.14",
            "Human oversight for high-risk AI",
            "fine_35M_or_7%"
        )
        req2 = engine.compliance.add_requirement(
            eu_ai_act,
            "Art.13",
            "Transparency obligations",
            "fine_35M_or_7%"
        )
        req3 = engine.compliance.add_requirement(
            eu_ai_act,
            "Art.10",
            "Data governance",
            "fine_35M_or_7%"
        )

        print(f"Added framework: EU AI Act ({eu_ai_act})")
        print("Requirements: Art.14 (human oversight), Art.13 (transparency), Art.10 (data)")

        # Add controls
        print("\n--- Adding Controls ---")
        ctrl1 = engine.compliance.add_control(
            "human_review_workflow",
            "procedural",
            automated=False,
            description="Human review for decisions"
        )
        ctrl2 = engine.compliance.add_control(
            "explanation_generator",
            "technical",
            automated=True,
            description="Automatic decision explanations"
        )

        # Map controls to requirements
        engine.compliance.map_control_to_requirement(req1, ctrl1, 0.85, "async_review_delay")
        engine.compliance.map_control_to_requirement(req2, ctrl2, 0.90)

        print("Controls: human_review_workflow, explanation_generator")
        print("Mappings: Art.14 -> human_review (85%), Art.13 -> explanation (90%)")

        # Check compliance
        print("\n--- Compliance Status ---")
        summary = engine.compliance.get_framework_compliance_summary(eu_ai_act)
        print(f"Total requirements: {summary['total_requirements']}")
        print(f"Compliant: {summary['compliant']}")
        print(f"Non-compliant: {summary['non_compliant']}")
        print(f"Compliance rate: {summary['compliance_rate']:.0%}")

        if summary["gaps"]:
            print("\nGaps:")
            for gap in summary["gaps"]:
                print(f"  - {gap['requirement']}: {gap['coverage']:.0%}")

        return engine


def example_risk_management():
    """
    Example: Risk assessment and management
    """
    print("\n" + "="*60)
    print("RISK MANAGEMENT")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        engine = quick_governance("risk-demo", setup_defaults=True)

        print("\n--- Default Risk Posture ---")
        posture = engine.assess_risk_posture()
        print(f"Overall posture: {posture['posture']}")
        print(f"Risks tracked: {posture['total_risks']}")
        print(f"By level: {posture['by_level']}")

        # Add a threat
        print("\n--- Adding Threat ---")
        threat_id = engine.risk.add_threat(
            "prompt_injection",
            "high",
            "high",
            [],  # Will link later
            "Malicious prompts to manipulate agent"
        )
        print(f"Added threat: prompt_injection ({threat_id})")

        # Add a control
        print("\n--- Adding Control ---")
        from agent_governance.schema import ControlType
        control_id = engine.risk.add_control(
            "input_validation",
            ControlType.PREVENTIVE,
            0.7,
            "low",
            [threat_id]
        )
        print(f"Added control: input_validation (effectiveness: 70%)")

        # Record an incident
        print("\n--- Recording Incident ---")
        incident_id = engine.report_incident(
            IncidentSeverity.MEDIUM,
            "security",
            "Attempted prompt injection detected and blocked"
        )
        print(f"Recorded incident: {incident_id}")

        # Get updated posture
        print("\n--- Updated Risk Posture ---")
        posture = engine.assess_risk_posture()
        print(f"Overall posture: {posture['posture']}")

        return engine


def example_escalation_workflow():
    """
    Example: Human oversight and escalation
    """
    print("\n" + "="*60)
    print("ESCALATION WORKFLOW")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        engine = quick_governance("escalation-demo", setup_defaults=True)

        # Register human reviewers
        print("\n--- Registering Reviewers ---")
        engine.escalation.add_reviewer(
            "Security Team",
            ["security", "data"],
            "24/7"
        )
        engine.escalation.add_reviewer(
            "Compliance Officer",
            ["regulatory", "compliance"],
            "business"
        )
        print("Reviewers: Security Team (24/7), Compliance Officer (business hours)")

        # Add escalation triggers
        print("\n--- Adding Triggers ---")
        engine.escalation.add_trigger(
            "confidence < 0.7",
            EscalationLevel.L3_OPERATOR,
            "1hr",
            "uncertain_decision"
        )
        engine.escalation.add_trigger(
            "safety_score < 0.5",
            EscalationLevel.L5_EXECUTIVE,
            "none",
            "safety_concern"
        )
        print("Triggers: low confidence -> L3, low safety -> L5")

        # Trigger an escalation
        print("\n--- Triggering Escalation ---")
        escalation_ids = engine.escalation.trigger_escalation({
            "confidence": 0.6,
            "agent_id": "agent_1",
            "action": "write_external"
        })

        if escalation_ids:
            print(f"Escalation created: {escalation_ids[0]}")

            # Get escalation details
            esc = engine.escalation.get_escalation(escalation_ids[0])
            print(f"Level: {esc.get('level')}")
            print(f"Status: {esc.get('status')}")
            print(f"Assigned to: {esc.get('assigned_to', 'unassigned')}")

            # Resolve it
            print("\n--- Resolving Escalation ---")
            engine.escalation.resolve_escalation(
                escalation_ids[0],
                "approved",
                "Action verified safe by human reviewer"
            )
            print("Escalation resolved: approved")

            # Record feedback
            engine.escalation.record_feedback(
                escalation_ids[0],
                "approved",
                "would_deny",
                "Agent threshold too conservative for this case"
            )
            print("Feedback recorded for learning")

        return engine


def example_multi_agent_coordination():
    """
    Example: Multi-agent group governance
    """
    print("\n" + "="*60)
    print("MULTI-AGENT COORDINATION")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        engine = quick_governance("coordination-demo", setup_defaults=True)

        # Create an agent group
        print("\n--- Creating Agent Group ---")
        group_id = engine.coordination.create_group(
            "research_swarm",
            "Parallel research task execution",
            "dynamic"
        )
        print(f"Created group: research_swarm ({group_id})")

        # Assign roles
        print("\n--- Assigning Roles ---")
        engine.coordination.assign_role(group_id, "agent_1", "coordinator", "task_assignment", "session")
        engine.coordination.assign_role(group_id, "agent_2", "worker", "execute_assigned", "session")
        engine.coordination.assign_role(group_id, "agent_3", "worker", "execute_assigned", "session")
        print("Roles: agent_1 (coordinator), agent_2 (worker), agent_3 (worker)")

        # Add protocols
        print("\n--- Adding Protocols ---")
        engine.coordination.add_protocol(
            group_id,
            "task_distribution",
            "coordinator_assigns_round_robin",
            "state_validator"
        )
        engine.coordination.add_protocol(
            group_id,
            "conflict",
            "coordinator_arbitrates",
            "coordinator"
        )
        print("Protocols: task_distribution (round robin), conflict (coordinator arbitrates)")

        # Check coordination authority
        print("\n--- Checking Coordination Authority ---")
        auth1 = engine.coordination.check_coordination_authority("agent_1", group_id, "task_assignment")
        print(f"agent_1 can assign tasks: {auth1['authorized']}")

        auth2 = engine.coordination.check_coordination_authority("agent_2", group_id, "task_assignment")
        print(f"agent_2 can assign tasks: {auth2['authorized']}")
        if not auth2["authorized"]:
            print(f"  Reason: {auth2['reason']}")

        # Record a violation
        print("\n--- Recording Violation ---")
        protocol = engine.coordination.get_group_protocols(group_id)[0]
        engine.coordination.record_violation(
            "agent_2",
            protocol["id"],
            "self_assigned_task",
            "reverted_warned"
        )
        print("Violation recorded: agent_2 self-assigned task (reverted)")

        # Get metrics
        print("\n--- Coordination Metrics ---")
        metrics = engine.coordination.get_coordination_metrics(group_id)
        print(f"Members: {metrics['member_count']}")
        print(f"Protocols: {metrics['protocol_count']}")
        print(f"Violations: {metrics['violation_count']}")
        print(f"Health: {metrics['health']}")

        return engine


def example_value_alignment():
    """
    Example: Ethics and value alignment
    """
    print("\n" + "="*60)
    print("VALUE ALIGNMENT")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        engine = quick_governance("ethics-demo", setup_defaults=True)

        print("\n--- Core Values (Default) ---")
        values = engine.ethics.list_values()
        for v in values:
            print(f"  - {v.get('name')}: {v.get('priority')} priority")

        # Add an ethical principle
        print("\n--- Adding Ethical Principle ---")
        safety_value = [v for v in values if v.get("name") == "safety"][0]
        principle_id = engine.ethics.add_principle(
            "do_no_harm",
            [safety_value["id"]],
            "safety_score > 0.7",
            "Agent actions must not cause harm"
        )
        print(f"Added principle: do_no_harm ({principle_id})")

        # Add a dilemma
        print("\n--- Adding Ethical Dilemma ---")
        user_benefit = [v for v in values if v.get("name") == "user_benefit"][0]
        dilemma_id = engine.ethics.add_dilemma(
            "user_requests_harmful",
            [user_benefit["id"], safety_value["id"]],
            "safety_over_request",
            ["User asks agent to do something harmful"]
        )
        print(f"Added dilemma: user requests harmful action")
        print("Resolution: safety over user request")

        # Resolve a dilemma
        print("\n--- Resolving Dilemma ---")
        resolution = engine.ethics.resolve_dilemma(
            "user requests potentially harmful",
            {}
        )
        if resolution.get("dilemma_matched"):
            print(f"Matched dilemma: {resolution.get('situation')}")
            print(f"Resolution principle: {resolution.get('resolution_principle')}")
            if resolution.get("dominant_value"):
                print(f"Dominant value: {resolution['dominant_value'].get('name')}")

        # Calculate alignment score
        print("\n--- Alignment Score ---")
        # First record some measurements
        for v in values[:3]:
            engine.ethics.record_measurement(v["id"], "compliance", 0.92, 0.95)

        alignment = engine.ethics.calculate_alignment_score("agent_1")
        print(f"Agent alignment score: {alignment.get('overall_score', 0):.2%}")
        print(f"Violations: {alignment.get('violation_count', 0)}")

        return engine


def main():
    """Run all examples"""
    example_basic_setup()
    example_policy_enforcement()
    example_compliance_tracking()
    example_risk_management()
    example_escalation_workflow()
    example_multi_agent_coordination()
    example_value_alignment()

    print("\n" + "="*60)
    print("ALL EXAMPLES COMPLETE")
    print("="*60)
    print("""
Key Governance Principles:

1. AUTHORITY CONTROL
   - Hierarchical delegation with decay
   - Time-bound permissions
   - Capability-based access

2. POLICY ENFORCEMENT
   - Declarative rules with precedence
   - Exception handling
   - Audit trail for all evaluations

3. COMPLIANCE TRACKING
   - Framework mapping (GDPR, EU AI Act, etc.)
   - Control coverage tracking
   - Gap analysis

4. RISK MANAGEMENT
   - Threat modeling
   - Control effectiveness
   - Appetite boundaries

5. HUMAN OVERSIGHT
   - Escalation paths
   - Fatigue management
   - Feedback learning

6. VALUE ALIGNMENT
   - Core values hierarchy
   - Ethical principles
   - Dilemma resolution

7. OBSERVABILITY
   - Health metrics
   - Pattern detection
   - Dashboards
""")


if __name__ == "__main__":
    main()
