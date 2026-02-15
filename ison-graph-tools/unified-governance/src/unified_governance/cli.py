"""
Unified Governance CLI
======================

Command-line interface for unified governance management.
"""

import argparse
import json
from pathlib import Path

from ison_graph import ISONGraph

from .engine import UnifiedGovernanceEngine, quick_unified_governance
from .schema import RegulationJurisdiction


def main():
    parser = argparse.ArgumentParser(
        description="Unified Governance CLI for ISONGraph"
    )
    parser.add_argument(
        "--graph", "-g",
        default="unified_governance.json",
        help="Path to graph file (default: unified_governance.json)"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize unified governance")
    init_parser.add_argument("--name", default="unified", help="Governance name")

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate governance report")
    report_parser.add_argument("--executive", action="store_true",
                              help="Generate executive summary")

    # Subject commands
    subject_parser = subparsers.add_parser("subject", help="Subject management")
    subject_sub = subject_parser.add_subparsers(dest="subject_cmd")

    subject_add = subject_sub.add_parser("add", help="Add unified subject")
    subject_add.add_argument("--id", required=True)
    subject_add.add_argument("--email", default="")
    subject_add.add_argument("--name", default="")
    subject_add.add_argument("--gdpr-id", default="")
    subject_add.add_argument("--ccpa-id", default="")
    subject_add.add_argument("--jurisdiction", default="global",
                            choices=[j.value for j in RegulationJurisdiction])

    subject_show = subject_sub.add_parser("show", help="Show subject details")
    subject_show.add_argument("subject_id")

    subject_status = subject_sub.add_parser("status", help="Show cross-regulation status")
    subject_status.add_argument("subject_id")

    # Agent commands
    agent_parser = subparsers.add_parser("agent", help="Agent PII access management")
    agent_sub = agent_parser.add_subparsers(dest="agent_cmd")

    agent_grant = agent_sub.add_parser("grant", help="Grant PII access")
    agent_grant.add_argument("--agent-id", required=True)
    agent_grant.add_argument("--pii-types", required=True, help="Comma-separated PII types")
    agent_grant.add_argument("--purpose", required=True)
    agent_grant.add_argument("--legal-basis", default="")

    agent_check = agent_sub.add_parser("check", help="Check agent access")
    agent_check.add_argument("agent_id")
    agent_check.add_argument("pii_type")

    # Compliance commands
    compliance_parser = subparsers.add_parser("compliance", help="Compliance checking")
    compliance_sub = compliance_parser.add_subparsers(dest="compliance_cmd")

    compliance_check = compliance_sub.add_parser("check", help="Check action compliance")
    compliance_check.add_argument("--agent-id", required=True)
    compliance_check.add_argument("--action", required=True)
    compliance_check.add_argument("--pii-types", required=True, help="Comma-separated")
    compliance_check.add_argument("--subject-id", default="")

    # Regulations command
    reg_parser = subparsers.add_parser("regulations", help="Regulation information")
    reg_sub = reg_parser.add_subparsers(dest="reg_cmd")

    reg_pii = reg_sub.add_parser("for-pii", help="Get regulations for PII type")
    reg_pii.add_argument("pii_type")

    reg_cross = reg_sub.add_parser("requirements", help="Cross-regulation requirements")
    reg_cross.add_argument("--pii-types", required=True, help="Comma-separated")

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show statistics")

    args = parser.parse_args()

    # Load or create graph
    graph_path = Path(args.graph)

    if args.command == "init":
        engine = quick_unified_governance(args.name, setup_defaults=True)
        engine.save(str(graph_path))
        print(f"Initialized unified governance at {graph_path}")
        return

    # Load existing
    if not graph_path.exists():
        print(f"Graph file not found: {graph_path}")
        print("Run 'unified-governance init' first")
        return

    graph = ISONGraph()
    graph.load(str(graph_path))
    engine = UnifiedGovernanceEngine(graph=graph)

    if args.command == "report":
        if args.executive:
            print(engine.get_executive_summary())
        else:
            report = engine.get_unified_report()
            print(json.dumps(report, indent=2, default=str))

    elif args.command == "subject":
        if args.subject_cmd == "add":
            subject_id = engine.register_subject(
                subject_id=args.id,
                email=args.email,
                name=args.name,
                gdpr_data_subject_id=args.gdpr_id or None,
                ccpa_consumer_id=args.ccpa_id or None,
                jurisdiction=RegulationJurisdiction(args.jurisdiction),
            )
            print(f"Added subject: {subject_id}")
            engine.save(str(graph_path))

        elif args.subject_cmd == "show":
            subject = engine.subjects.get_unified_subject(args.subject_id)
            if subject:
                print(json.dumps(subject, indent=2, default=str))
            else:
                print(f"Subject not found: {args.subject_id}")

        elif args.subject_cmd == "status":
            status = engine.subjects.get_cross_regulation_status(args.subject_id)
            print(json.dumps(status, indent=2, default=str))

    elif args.command == "agent":
        if args.agent_cmd == "grant":
            pii_types = [p.strip() for p in args.pii_types.split(",")]
            access_id = engine.grant_agent_pii_access(
                agent_id=args.agent_id,
                pii_types=pii_types,
                purpose=args.purpose,
                legal_basis=args.legal_basis,
            )
            print(f"Granted access: {access_id}")
            engine.save(str(graph_path))

        elif args.agent_cmd == "check":
            result = engine.agent_integration.check_agent_pii_access(
                args.agent_id, args.pii_type
            )
            print(json.dumps(result, indent=2, default=str))

    elif args.command == "compliance":
        if args.compliance_cmd == "check":
            pii_types = [p.strip() for p in args.pii_types.split(",")]
            result = engine.check_compliance(
                agent_id=args.agent_id,
                action=args.action,
                pii_types=pii_types,
                data_subject_id=args.subject_id or None,
            )

            print(f"\nCompliance Check: {result['check_id']}")
            print("=" * 50)
            print(f"Agent: {result['agent_id']}")
            print(f"Action: {result['action']}")
            print(f"PII Types: {', '.join(result['pii_types'])}")
            print(f"\nPermitted: {result['permitted']}")
            print(f"Status: {result['overall_status']}")
            print(f"Risk Level: {result['risk_level']}")

            if result['blocking_issues']:
                print(f"\nBlocking Issues ({len(result['blocking_issues'])}):")
                for issue in result['blocking_issues']:
                    print(f"  - {issue.get('issue', issue)}")

            if result['warnings']:
                print(f"\nWarnings ({len(result['warnings'])}):")
                for warning in result['warnings']:
                    print(f"  - {warning.get('issue', warning)}")

            if result['recommendations']:
                print(f"\nRecommendations:")
                for rec in result['recommendations']:
                    print(f"  - {rec}")

    elif args.command == "regulations":
        if args.reg_cmd == "for-pii":
            result = engine.regulatory.get_regulations_for_pii(args.pii_type)
            print(f"\nRegulations for PII type: {args.pii_type}")
            print("-" * 40)
            for reg, info in result["applicable_regulations"].items():
                print(f"  {reg}:")
                print(f"    Requirements: {', '.join(info.get('requirements', []))}")

        elif args.reg_cmd == "requirements":
            pii_types = [p.strip() for p in args.pii_types.split(",")]
            result = engine.regulatory.get_cross_regulation_requirements(pii_types)
            print(f"\nCross-Regulation Requirements")
            print("-" * 40)
            print(f"PII Types: {', '.join(result['pii_types_analyzed'])}")
            print(f"Applicable Regulations: {', '.join(result['applicable_regulations'])}")
            print("\nRequirements by Regulation:")
            for reg, reqs in result["requirements_by_regulation"].items():
                print(f"  {reg}: {', '.join(reqs)}")

    elif args.command == "stats":
        report = engine.get_unified_report()
        health = report['health']

        print("\nUnified Governance Statistics")
        print("=" * 50)
        print(f"Overall Health Score: {health['overall_score']}/100")
        print(f"Status: {health['status'].upper()}")
        print(f"Critical Items: {health['critical_items']}")
        print(f"Compliance Gaps: {health['compliance_gaps']}")

        print("\nCross-Domain Stores:")
        for store, stats in report.get("cross_domain", {}).items():
            print(f"\n  {store}:")
            for key, value in stats.items():
                if not key.startswith("_"):
                    print(f"    {key}: {value}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
