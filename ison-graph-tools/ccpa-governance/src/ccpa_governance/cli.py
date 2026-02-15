"""
CCPA Governance CLI
===================

Command-line interface for CCPA compliance management.
"""

import argparse
import json
from pathlib import Path

from ison_graph import ISONGraph

from .engine import CCPAGovernance
from .schema import (
    PersonalInfoCategory, ConsumerRight, NoticeType, BusinessRole
)


def main():
    parser = argparse.ArgumentParser(
        description="CCPA Governance CLI for ISONGraph"
    )
    parser.add_argument(
        "--graph", "-g",
        default="ccpa_graph.json",
        help="Path to graph file (default: ccpa_graph.json)"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Status command
    status_parser = subparsers.add_parser("status", help="Get compliance status")

    # Consumer commands
    consumer_parser = subparsers.add_parser("consumer", help="Consumer management")
    consumer_sub = consumer_parser.add_subparsers(dest="consumer_cmd")

    consumer_add = consumer_sub.add_parser("add", help="Add consumer")
    consumer_add.add_argument("--id", required=True)
    consumer_add.add_argument("--email")
    consumer_add.add_argument("--california", action="store_true", default=True)

    consumer_get = consumer_sub.add_parser("get", help="Get consumer")
    consumer_get.add_argument("consumer_id")

    consumer_opt_out = consumer_sub.add_parser("opt-out", help="Process opt-out")
    consumer_opt_out.add_argument("consumer_id")
    consumer_opt_out.add_argument("--sale", action="store_true")
    consumer_opt_out.add_argument("--share", action="store_true")

    # Request commands
    request_parser = subparsers.add_parser("request", help="Consumer requests")
    request_sub = request_parser.add_subparsers(dest="request_cmd")

    request_submit = request_sub.add_parser("submit", help="Submit request")
    request_submit.add_argument("--consumer", required=True)
    request_submit.add_argument("--type", required=True,
                               choices=["know", "delete", "correct", "opt_out_sale"])

    request_pending = request_sub.add_parser("pending", help="List pending")
    request_overdue = request_sub.add_parser("overdue", help="List overdue")

    # Notice commands
    notice_parser = subparsers.add_parser("notice", help="Notice management")
    notice_sub = notice_parser.add_subparsers(dest="notice_cmd")

    notice_check = notice_sub.add_parser("check", help="Check compliance")
    notice_list = notice_sub.add_parser("list", help="List notices")

    # Disclosure report
    disclosure_parser = subparsers.add_parser("disclosure", help="Disclosure report")

    args = parser.parse_args()

    # Load or create graph
    graph_path = Path(args.graph)
    graph = ISONGraph()
    if graph_path.exists():
        graph.load(str(graph_path))

    ccpa = CCPAGovernance(graph)

    if args.command == "status":
        status = ccpa.get_compliance_status()
        print(f"\nCCPA Compliance Status")
        print("=" * 50)
        print(f"Compliance Score: {status['compliance_score']}/100")
        print(f"\nSummary:")
        for key, value in status['summary'].items():
            print(f"  {key}: {value}")
        if status['issues']:
            print(f"\nIssues ({len(status['issues'])}):")
            for issue in status['issues']:
                print(f"  [{issue['severity']}] {issue['issue']}")

    elif args.command == "consumer":
        if args.consumer_cmd == "add":
            consumer_id = ccpa.consumers.register_consumer(
                consumer_id=args.id,
                email=args.email,
                is_california_resident=args.california,
            )
            print(f"Added consumer: {consumer_id}")
            graph.save(str(graph_path))

        elif args.consumer_cmd == "get":
            consumer = ccpa.consumers.get_consumer(args.consumer_id)
            if consumer:
                print(json.dumps(consumer, indent=2))
            else:
                print("Consumer not found")

        elif args.consumer_cmd == "opt-out":
            result = ccpa.process_opt_out(
                consumer_id=args.consumer_id,
                opt_out_sale=args.sale,
                opt_out_share=args.share,
            )
            print(f"Opt-out processed: {result}")
            graph.save(str(graph_path))

    elif args.command == "request":
        right_map = {
            "know": ConsumerRight.RIGHT_TO_KNOW,
            "delete": ConsumerRight.RIGHT_TO_DELETE,
            "correct": ConsumerRight.RIGHT_TO_CORRECT,
            "opt_out_sale": ConsumerRight.RIGHT_TO_OPT_OUT_SALE,
        }

        if args.request_cmd == "submit":
            request_id = ccpa.rights.submit_request(
                consumer_id=args.consumer,
                right_type=right_map[args.type],
            )
            print(f"Submitted request: {request_id}")
            graph.save(str(graph_path))

        elif args.request_cmd == "pending":
            pending = ccpa.rights.get_pending_requests()
            print(f"\nPending Requests ({len(pending)}):")
            for r in pending:
                print(f"  - {r['id']}: {r['right_type']} ({r['status']})")

        elif args.request_cmd == "overdue":
            overdue = ccpa.rights.get_overdue_requests()
            print(f"\nOverdue Requests ({len(overdue)}):")
            for r in overdue:
                print(f"  - {r['id']}: deadline was {r['deadline']}")

    elif args.command == "notice":
        if args.notice_cmd == "check":
            compliance = ccpa.notices.check_notice_compliance()
            print(f"\nNotice Compliance: {'PASS' if compliance['all_notices_present'] else 'FAIL'}")
            for notice_type, status in compliance['notices'].items():
                status_str = "Present" if status['exists'] else "MISSING"
                print(f"  {notice_type}: {status_str}")

        elif args.notice_cmd == "list":
            stats = ccpa.notices.get_stats()
            print(f"\nNotices: {stats['total_notices']} total, {stats['current_notices']} current")

    elif args.command == "disclosure":
        disclosure = ccpa.get_disclosure_report()
        print("\nDisclosure Report")
        print("=" * 50)
        print(f"Categories collected: {disclosure['categories_collected']}")
        print(f"Categories sold (12mo): {list(disclosure['categories_sold_12_months'].keys())}")
        print(f"Categories shared (12mo): {list(disclosure['categories_shared_12_months'].keys())}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
