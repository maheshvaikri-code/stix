"""
PII Governance CLI
==================

Command-line interface for PII governance management.
"""

import argparse
import json
from pathlib import Path

from ison_graph import ISONGraph

from .engine import PIIGovernance
from .schema import (
    DataSourceType, StorageLocation, SensitivityLevel,
    ProtectionStatus, Regulation
)


def main():
    parser = argparse.ArgumentParser(
        description="PII Governance CLI for ISONGraph"
    )
    parser.add_argument(
        "--graph", "-g",
        default="pii_graph.json",
        help="Path to graph file (default: pii_graph.json)"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate governance report")
    report_parser.add_argument("--executive", action="store_true",
                              help="Generate executive summary")

    # Source commands
    source_parser = subparsers.add_parser("source", help="Data source management")
    source_sub = source_parser.add_subparsers(dest="source_cmd")

    source_add = source_sub.add_parser("add", help="Add data source")
    source_add.add_argument("--id", required=True)
    source_add.add_argument("--name", required=True)
    source_add.add_argument("--type", required=True,
                           choices=[t.value for t in DataSourceType])
    source_add.add_argument("--location", required=True,
                           choices=[l.value for l in StorageLocation])
    source_add.add_argument("--owner", required=True)

    source_list = source_sub.add_parser("list", help="List data sources")

    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan for PII")
    scan_sub = scan_parser.add_subparsers(dest="scan_cmd")

    scan_text = scan_sub.add_parser("text", help="Scan text for PII")
    scan_text.add_argument("text", help="Text to scan")

    # Inventory commands
    inv_parser = subparsers.add_parser("inventory", help="PII inventory")
    inv_sub = inv_parser.add_subparsers(dest="inv_cmd")

    inv_list = inv_sub.add_parser("list", help="List inventory")
    inv_list.add_argument("--source", help="Filter by source")

    inv_unprotected = inv_sub.add_parser("unprotected", help="Show unprotected PII")
    inv_high_risk = inv_sub.add_parser("high-risk", help="Show high risk items")

    # Map command
    map_parser = subparsers.add_parser("map", help="Show PII map")
    map_parser.add_argument("--pii-type", help="Filter by PII type")

    # Assessment commands
    assess_parser = subparsers.add_parser("assess", help="Risk assessment")
    assess_sub = assess_parser.add_subparsers(dest="assess_cmd")

    assess_source = assess_sub.add_parser("source", help="Assess a data source")
    assess_source.add_argument("source_id", help="Source ID to assess")
    assess_source.add_argument("--assessor", default="cli_user")

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show statistics")

    args = parser.parse_args()

    # Load or create graph
    graph_path = Path(args.graph)
    graph = ISONGraph()
    if graph_path.exists():
        graph.load(str(graph_path))

    pii = PIIGovernance(graph)

    if args.command == "report":
        if args.executive:
            print(pii.get_executive_summary())
        else:
            report = pii.get_governance_report()
            print(f"\nPII Governance Report")
            print("=" * 50)
            print(f"Governance Score: {report['governance_score']}/100")
            print(f"\nSummary:")
            for key, value in report['summary'].items():
                print(f"  {key}: {value}")
            if report['issues']:
                print(f"\nIssues ({len(report['issues'])}):")
                for issue in report['issues']:
                    print(f"  [{issue['severity']}] {issue['issue']}")

    elif args.command == "source":
        if args.source_cmd == "add":
            source_id = pii.inventory.register_data_source(
                source_id=args.id,
                name=args.name,
                source_type=DataSourceType(args.type),
                storage_location=StorageLocation(args.location),
                owner=args.owner,
            )
            print(f"Added data source: {source_id}")
            graph.save(str(graph_path))

        elif args.source_cmd == "list":
            sources = pii.inventory.list_data_sources()
            print(f"\nData Sources ({len(sources)}):")
            for s in sources:
                print(f"  - {s['id']}: {s['name']} ({s['source_type']})")

    elif args.command == "scan":
        if args.scan_cmd == "text":
            result = pii.scan_text_for_pii(args.text)
            print(f"\nScan Results:")
            print(f"  Total detections: {result['total_detections']}")
            for d in result['detections']:
                print(f"  - {d['pii_type']}: '{d['matched_text']}'")

    elif args.command == "inventory":
        if args.inv_cmd == "list":
            if args.source:
                items = pii.inventory.get_inventory_by_source(args.source)
            else:
                items = []
                for node in pii.graph.nodes():
                    if node.type == "pii_inventory_item":
                        items.append(pii.inventory.get_inventory_item(node.id))
            print(f"\nPII Inventory ({len(items)} items):")
            for item in items:
                print(f"  - {item['pii_type']} @ {item['field_location']} "
                      f"({item['sensitivity']}, {item['protection_status']})")

        elif args.inv_cmd == "unprotected":
            items = pii.inventory.get_unprotected_inventory()
            print(f"\nUnprotected PII ({len(items)} items):")
            for item in items:
                print(f"  - {item['pii_type']} @ {item['source_id']}: {item['field_location']}")

        elif args.inv_cmd == "high-risk":
            items = pii.inventory.get_high_risk_inventory()
            print(f"\nHigh Risk PII ({len(items)} items):")
            for item in items:
                print(f"  - {item['pii_type']} @ {item['source_id']} "
                      f"(risk: {item['risk_level']})")

    elif args.command == "map":
        pii_map = pii.get_pii_map()
        print(f"\nPII Map ({pii_map['sources_with_pii']} sources):")
        for source_id, info in pii_map['map'].items():
            print(f"\n  {source_id}:")
            for pii_type, fields in info['pii_types'].items():
                print(f"    - {pii_type}: {len(fields)} field(s)")

    elif args.command == "assess":
        if args.assess_cmd == "source":
            result = pii.assess_data_source_risk(
                source_id=args.source_id,
                assessor=args.assessor,
            )
            print(f"\nRisk Assessment: {result['assessment_id']}")
            print(f"  Sensitivity Score: {result['scores']['sensitivity_score']}")
            print(f"  Protection Score: {result['scores']['protection_score']}")
            print(f"  Overall Risk: {result['scores']['overall_risk_level']}")
            graph.save(str(graph_path))

    elif args.command == "stats":
        class_stats = pii.classification.get_stats()
        inv_stats = pii.inventory.get_stats()
        risk_stats = pii.risk.get_stats()
        lineage_stats = pii.lineage.get_stats()

        print("\nPII Governance Statistics")
        print("=" * 50)
        print(f"\nClassification:")
        print(f"  Total: {class_stats['total_classifications']}")
        print(f"  Verified: {class_stats['verified_classifications']}")
        print(f"\nInventory:")
        print(f"  Data Sources: {inv_stats['total_data_sources']}")
        print(f"  Items: {inv_stats['total_inventory_items']}")
        print(f"  Unprotected: {inv_stats['unprotected_items']}")
        print(f"\nRisk Assessments: {risk_stats['total_assessments']}")
        print(f"Data Flows: {lineage_stats['total_data_flows']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
