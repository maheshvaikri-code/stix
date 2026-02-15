# Agent Governance

Comprehensive Governance Layer for AI Agents built on ISONGraph.

## Overview

Agent Governance provides a complete framework for governing AI agent behavior across 15 domains:

1. **Authority & Delegation** - Who can authorize what
2. **Policy Engine** - Rules, conditions, and evaluation
3. **Compliance Framework** - GDPR, HIPAA, SOX, EU AI Act mapping
4. **Audit Trail** - Decision provenance and accountability
5. **Risk Assessment** - Threats, controls, and mitigation
6. **Human Oversight** - Escalation and review workflows
7. **Resource Governance** - Budgets and allocation
8. **Multi-Agent Coordination** - Group governance protocols
9. **Ethics & Values** - Value alignment and dilemmas
10. **Capability Governance** - Feature flags and grants
11. **Incident Response** - Detection and recovery
12. **Meta-Governance** - Governing the governance
13. **Cross-Organizational** - Trust and agreements
14. **Temporal Governance** - Time-bound authority
15. **Observability** - Metrics and dashboards

## Installation

```bash
pip install agent-governance
```

## Quick Start

```python
from agent_governance import GovernanceEngine, quick_governance

# Quick setup with defaults
engine = quick_governance("my-agent-system")

# Register an agent
engine.register_agent("agent_1", "Research Agent")

# Check if an action is permitted
result = engine.check_action(
    agent_id="agent_1",
    action="write_external",
    context={"data_classification": "internal"}
)

if result["permitted"]:
    print("Action allowed")
elif result["escalation_required"]:
    print("Needs human approval")
else:
    print(f"Denied: {result['reason']}")
```

## Key Features

### Authority Control
```python
# Grant authority with conditions
engine.authority.grant_authority("agent_1", "read_public", "public_only")

# Delegate authority
engine.authority.delegate("admin", "agent_1", ["read_internal"], expires_at="2025-01-01")
```

### Policy Enforcement
```python
# Add policies with rules
engine.add_policy("safety", [
    {"condition": "safety_score < 0.5", "action": "deny"},
    {"condition": "confidence < 0.7", "action": "escalate"}
])
```

### Compliance Tracking
```python
# Add framework and requirements
framework_id = engine.compliance.add_framework("EU AI Act", "EU", "2024-08-01", "ai_systems")
engine.compliance.add_requirement(framework_id, "Art.14", "Human oversight", "fine_35M")
```

### Risk Management
```python
# Track risks and controls
risk_id = engine.risk.add_risk("safety", "harmful_content", 0.9, 0.3)
engine.risk.add_control("output_filter", ControlType.PREVENTIVE, 0.8, "low", [])
```

### Human Oversight
```python
# Trigger escalation
engine.escalation.trigger_escalation({
    "confidence": 0.6,
    "action": "write_external"
})
```

### Value Alignment
```python
# Check ethical alignment
alignment = engine.ethics.calculate_alignment_score("agent_1")
print(f"Alignment: {alignment['overall_score']:.0%}")
```

## CLI Usage

```bash
# Initialize governance
agov init my-project

# Check status
agov status ./my-project-governance/governance.ison

# Check action permission
agov check ./governance.ison agent_1 write_external

# View health metrics
agov health ./governance.ison

# List incidents
agov incidents ./governance.ison
```

## Architecture

The governance system is built on ISONGraph and provides:

- **Graph-based storage** for complex relationships
- **ISONQL queries** for governance analysis
- **Persistent state** with save/load
- **Comprehensive audit trails**
- **Real-time metrics**

## License

MIT
