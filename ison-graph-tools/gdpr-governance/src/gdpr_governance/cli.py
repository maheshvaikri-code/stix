"""
GDPR Governance CLI
===================

Command-line interface for GDPR compliance management.
"""

import argparse
import json
import sys
from pathlib import Path

from ison_graph import ISONGraph

from .engine import GDPRGovernance
from .schema import (
    LawfulBasis, PersonalDataCategory, ConsentType,
    DataSubjectRight, BreachSeverity, BreachType,
    DPIATrigger, TransferMechanism, ActorRole
)


def main():
    parser = argparse.ArgumentParser(
        description="GDPR Governance CLI for ISONGraph"
    )
    parser.add_argument(
        "--graph", "-g",
        default="gdpr_graph.json",
        help="Path to graph file (default: gdpr_graph.json)"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Status command
    status_parser = subparsers.add_parser("status", help="Get compliance status")

    # Processing commands
    proc_parser = subparsers.add_parser("processing", help="Processing activities")
    proc_sub = proc_parser.add_subparsers(dest="proc_cmd")

    proc_list = proc_sub.add_parser("list", help="List processing activities")
    proc_add = proc_sub.add_parser("add", help="Add processing activity")
    proc_add.add_argument("--name", required=True)
    proc_add.add_argument("--purpose", required=True)
    proc_add.add_argument("--lawful-basis", required=True,
                         choices=[b.value for b in LawfulBasis])
    proc_add.add_argument("--controller", required=True)

    # Consent commands
    consent_parser = subparsers.add_parser("consent", help="Consent management")
    consent_sub = consent_parser.add_subparsers(dest="consent_cmd")

    consent_record = consent_sub.add_parser("record", help="Record consent")
    consent_record.add_argument("--subject", required=True)
    consent_record.add_argument("--purpose", required=True)

    consent_withdraw = consent_sub.add_parser("withdraw", help="Withdraw consent")
    consent_withdraw.add_argument("--consent-id", required=True)

    consent_check = consent_sub.add_parser("check", help="Check consent")
    consent_check.add_argument("--subject", required=True)
    consent_check.add_argument("--purpose", required=True)

    # Rights commands
    rights_parser = subparsers.add_parser("rights", help="Data subject rights")
    rights_sub = rights_parser.add_subparsers(dest="rights_cmd")

    rights_submit = rights_sub.add_parser("submit", help="Submit DSR request")
    rights_submit.add_argument("--subject", required=True)
    rights_submit.add_argument("--type", required=True,
                              choices=[r.value for r in DataSubjectRight])

    rights_pending = rights_sub.add_parser("pending", help="List pending requests")
    rights_overdue = rights_sub.add_parser("overdue", help="List overdue requests")

    # Breach commands
    breach_parser = subparsers.add_parser("breach", help="Breach management")
    breach_sub = breach_parser.add_subparsers(dest="breach_cmd")

    breach_report = breach_sub.add_parser("report", help="Report breach")
    breach_report.add_argument("--description", required=True)
    breach_report.add_argument("--type", default="confidentiality",
                              choices=[b.value for b in BreachType])

    breach_list = breach_sub.add_parser("list", help="List open breaches")

    # DPIA commands
    dpia_parser = subparsers.add_parser("dpia", help="DPIA management")
    dpia_sub = dpia_parser.add_subparsers(dest="dpia_cmd")

    dpia_list = dpia_sub.add_parser("list", help="List DPIAs")
    dpia_required = dpia_sub.add_parser("required", help="List required DPIAs")

    # Transfer commands
    transfer_parser = subparsers.add_parser("transfer", help="International transfers")
    transfer_sub = transfer_parser.add_subparsers(dest="transfer_cmd")

    transfer_list = transfer_sub.add_parser("list", help="List transfers")
    transfer_adequacy = transfer_sub.add_parser("adequacy", help="Check adequacy")
    transfer_adequacy.add_argument("country")

    # ROPA export
    ropa_parser = subparsers.add_parser("ropa", help="Export ROPA")
    ropa_parser.add_argument("--output", "-o", help="Output file")

    args = parser.parse_args()

    # Load or create graph
    graph_path = Path(args.graph)
    graph = ISONGraph()
    if graph_path.exists():
        graph.load(str(graph_path))

    gdpr = GDPRGovernance(graph)

    # Execute command
    if args.command == "status":
        status = gdpr.get_compliance_status()
        print(f"\nGDPR Compliance Status")
        print("=" * 50)
        print(f"Compliance Score: {status['compliance_score']}/100")
        print(f"\nSummary:")
        for key, value in status['summary'].items():
            print(f"  {key}: {value}")
        if status['issues']:
            print(f"\nIssues ({len(status['issues'])}):")
            for issue in status['issues']:
                print(f"  [{issue['severity']}] {issue['issue']}")

    elif args.command == "processing":
        if args.proc_cmd == "list":
            activities = gdpr.processing.list_activities()
            print(f"\nProcessing Activities ({len(activities)}):")
            for a in activities:
                print(f"  - {a['name']}: {a['purpose'][:50]}")
        elif args.proc_cmd == "add":
            activity_id = gdpr.processing.register_activity(
                name=args.name,
                purpose=args.purpose,
                lawful_basis=LawfulBasis(args.lawful_basis),
                data_categories=[PersonalDataCategory.BASIC_IDENTITY],
                data_subjects=["general"],
                recipients=["internal"],
                retention_period="As specified",
                security_measures=["standard"],
                controller_id=args.controller,
            )
            print(f"Created activity: {activity_id}")
            graph.save(str(graph_path))

    elif args.command == "consent":
        if args.consent_cmd == "record":
            consent_id = gdpr.consent.record_consent(
                data_subject_id=args.subject,
                purpose=args.purpose,
            )
            print(f"Recorded consent: {consent_id}")
            graph.save(str(graph_path))
        elif args.consent_cmd == "withdraw":
            result = gdpr.consent.withdraw_consent(args.consent_id)
            print(f"Consent withdrawn: {result}")
            graph.save(str(graph_path))
        elif args.consent_cmd == "check":
            result = gdpr.consent.check_consent(args.subject, args.purpose)
            print(f"Has consent: {result['has_consent']}")

    elif args.command == "rights":
        if args.rights_cmd == "submit":
            request_id = gdpr.rights.submit_request(
                data_subject_id=args.subject,
                right_type=DataSubjectRight(args.type),
            )
            print(f"Submitted request: {request_id}")
            graph.save(str(graph_path))
        elif args.rights_cmd == "pending":
            pending = gdpr.rights.get_pending_requests()
            print(f"\nPending Requests ({len(pending)}):")
            for r in pending:
                print(f"  - {r['id']}: {r['right_type']} ({r['status']})")
        elif args.rights_cmd == "overdue":
            overdue = gdpr.rights.get_overdue_requests()
            print(f"\nOverdue Requests ({len(overdue)}):")
            for r in overdue:
                print(f"  - {r['id']}: {r['right_type']} (deadline: {r['deadline']})")

    elif args.command == "breach":
        if args.breach_cmd == "report":
            breach_id = gdpr.breach.report_breach(
                description=args.description,
                breach_type=BreachType(args.type),
            )
            breach = gdpr.breach.get_breach(breach_id)
            print(f"Reported breach: {breach_id}")
            print(f"72-hour deadline: {breach['dpa_deadline']}")
            graph.save(str(graph_path))
        elif args.breach_cmd == "list":
            breaches = gdpr.breach.get_open_breaches()
            print(f"\nOpen Breaches ({len(breaches)}):")
            for b in breaches:
                print(f"  - {b['id']}: {b['description'][:50]} ({b['status']})")

    elif args.command == "dpia":
        if args.dpia_cmd == "list":
            stats = gdpr.dpia.get_stats()
            print(f"\nDPIA Summary:")
            print(f"  Total: {stats['total_dpias']}")
            for status, count in stats['by_status'].items():
                print(f"  {status}: {count}")
        elif args.dpia_cmd == "required":
            required = gdpr.dpia.get_dpias_by_status(
                __import__('gdpr_governance.schema', fromlist=['DPIAStatus']).DPIAStatus.REQUIRED
            )
            print(f"\nRequired DPIAs ({len(required)}):")
            for d in required:
                print(f"  - {d['id']}: {d['name']}")

    elif args.command == "transfer":
        if args.transfer_cmd == "list":
            transfers = gdpr.transfer.get_active_transfers()
            print(f"\nActive Transfers ({len(transfers)}):")
            for t in transfers:
                print(f"  - {t['name']}: {t['source_country']} -> {t['destination_country']}")
        elif args.transfer_cmd == "adequacy":
            result = gdpr.transfer.check_adequacy(args.country)
            print(f"{args.country}: {'Has adequacy decision' if result['has_adequacy_decision'] else 'No adequacy decision'}")

    elif args.command == "ropa":
        ropa = gdpr.export_ropa()
        if args.output:
            with open(args.output, "w") as f:
                json.dump(ropa, f, indent=2)
            print(f"ROPA exported to {args.output}")
        else:
            print(json.dumps(ropa, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
