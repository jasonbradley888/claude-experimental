#!/usr/bin/env python3
"""
Knowledge Graph CLI

A command-line interface for the local knowledge graph.
Backward compatible with the original local_knowledge_graph.py commands.

Usage:
    # Existing commands (backward compatible)
    python -m knowledge_graph create-entities '[{"name": "AA_W_123", "type": "workflow"}]'
    python -m knowledge_graph create-relations '[["AA_W_123", "contains", "AA_T_task1"]]'
    python -m knowledge_graph add-observations "AA_W_123" '["Started: 2026-01-23"]'
    python -m knowledge_graph query --pattern "AA_T_*"
    python -m knowledge_graph get "AA_W_123"
    python -m knowledge_graph list
    python -m knowledge_graph export-mermaid "AA_W_123"
    python -m knowledge_graph delete-entity "AA_W_123"
    python -m knowledge_graph clear

    # New commands
    python -m knowledge_graph search "revenue recognition"
    python -m knowledge_graph shortest-path "A" "B"
    python -m knowledge_graph subgraph "root" --depth 3
    python -m knowledge_graph migrate-to-sqlite
    python -m knowledge_graph export-graphml
    python -m knowledge_graph export-dot
    python -m knowledge_graph visualize "AA_W_123"
    python -m knowledge_graph stats

    # Backend selection
    python -m knowledge_graph --backend sqlite list
    python -m knowledge_graph --backend json list
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ..core.graph import KnowledgeGraph
from ..core.models import Entity, Relation
from ..storage.migration import get_default_paths
from ..visualize.figma import FigmaVisualizer


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Knowledge Graph CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Global options
    parser.add_argument(
        "--backend",
        choices=["sqlite", "json"],
        default="sqlite",
        help="Storage backend (default: sqlite)"
    )
    parser.add_argument(
        "--path",
        type=Path,
        help="Path to storage file (uses default if not specified)"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # -------------------------------------------------------------------------
    # Existing commands (backward compatible)
    # -------------------------------------------------------------------------

    # create-entities
    create_ent = subparsers.add_parser(
        "create-entities",
        help="Create multiple entities"
    )
    create_ent.add_argument(
        "entities",
        help='JSON array of entities: [{"name": "...", "type": "..."}]'
    )

    # create-relations
    create_rel = subparsers.add_parser(
        "create-relations",
        help="Create multiple relations"
    )
    create_rel.add_argument(
        "relations",
        help='JSON array of [from, type, to] tuples'
    )

    # add-observations
    add_obs = subparsers.add_parser(
        "add-observations",
        help="Add observations to an entity"
    )
    add_obs.add_argument("entity", help="Entity name")
    add_obs.add_argument("observations", help='JSON array of observation strings')

    # query
    query_cmd = subparsers.add_parser("query", help="Query entities")
    query_cmd.add_argument("--pattern", help="Glob pattern to match entity names")
    query_cmd.add_argument("--type", dest="entity_type", help="Filter by entity type")
    query_cmd.add_argument("--related-to", help="Filter by relation to entity")
    query_cmd.add_argument("--created-after", help="Filter by creation date (ISO 8601)")
    query_cmd.add_argument("--created-before", help="Filter by creation date (ISO 8601)")

    # get
    get_cmd = subparsers.add_parser(
        "get",
        help="Get a single entity with relations"
    )
    get_cmd.add_argument("entity", help="Entity name")

    # list
    subparsers.add_parser("list", help="List all entities")

    # delete-entity
    del_cmd = subparsers.add_parser("delete-entity", help="Delete an entity")
    del_cmd.add_argument("entity", help="Entity name")

    # export-mermaid
    mermaid_cmd = subparsers.add_parser(
        "export-mermaid",
        help="Export as Mermaid diagram"
    )
    mermaid_cmd.add_argument("root", nargs="?", help="Optional root entity")
    mermaid_cmd.add_argument(
        "--direction",
        choices=["LR", "TB", "RL", "BT"],
        default="LR",
        help="Diagram direction"
    )
    mermaid_cmd.add_argument(
        "--no-styling",
        action="store_true",
        help="Exclude color styling"
    )

    # clear
    subparsers.add_parser("clear", help="Clear all entities and relations")

    # -------------------------------------------------------------------------
    # New commands
    # -------------------------------------------------------------------------

    # search (full-text)
    search_cmd = subparsers.add_parser(
        "search",
        help="Full-text search across entities"
    )
    search_cmd.add_argument("query", help="Search query")
    search_cmd.add_argument(
        "--fields",
        help="Comma-separated fields to search (name,type,observations)"
    )

    # shortest-path
    path_cmd = subparsers.add_parser(
        "shortest-path",
        help="Find shortest path between entities"
    )
    path_cmd.add_argument("source", help="Source entity")
    path_cmd.add_argument("target", help="Target entity")

    # subgraph
    subgraph_cmd = subparsers.add_parser(
        "subgraph",
        help="Extract subgraph around entity"
    )
    subgraph_cmd.add_argument("root", help="Root entity")
    subgraph_cmd.add_argument(
        "--depth",
        type=int,
        default=3,
        help="Maximum depth (default: 3)"
    )

    # migrate-to-sqlite
    migrate_cmd = subparsers.add_parser(
        "migrate-to-sqlite",
        help="Migrate JSON data to SQLite"
    )
    migrate_cmd.add_argument(
        "--json-path",
        type=Path,
        help="Source JSON file"
    )
    migrate_cmd.add_argument(
        "--sqlite-path",
        type=Path,
        help="Destination SQLite file"
    )
    migrate_cmd.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip JSON backup"
    )

    # export-graphml
    graphml_cmd = subparsers.add_parser(
        "export-graphml",
        help="Export as GraphML"
    )
    graphml_cmd.add_argument(
        "--output",
        "-o",
        help="Output file (prints to stdout if not specified)"
    )

    # export-dot
    dot_cmd = subparsers.add_parser(
        "export-dot",
        help="Export as DOT/Graphviz"
    )
    dot_cmd.add_argument(
        "--output",
        "-o",
        help="Output file"
    )
    dot_cmd.add_argument(
        "--direction",
        choices=["LR", "TB", "RL", "BT"],
        default="LR"
    )

    # visualize (Figma preparation)
    viz_cmd = subparsers.add_parser(
        "visualize",
        help="Prepare Figma diagram"
    )
    viz_cmd.add_argument("root", help="Root entity")
    viz_cmd.add_argument(
        "--depth",
        type=int,
        default=3,
        help="Maximum depth"
    )
    viz_cmd.add_argument("--title", help="Diagram title")
    viz_cmd.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of formatted"
    )

    # stats
    subparsers.add_parser("stats", help="Show storage statistics")

    # -------------------------------------------------------------------------
    # Parse and execute
    # -------------------------------------------------------------------------

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Handle migration separately (doesn't need a KG instance)
    if args.command == "migrate-to-sqlite":
        result = KnowledgeGraph.migrate_to_sqlite(
            json_path=args.json_path,
            sqlite_path=args.sqlite_path,
            backup_json=not args.no_backup
        )
        output = {
            "success": result.success,
            "entities_migrated": result.entities_migrated,
            "relations_migrated": result.relations_migrated,
            "observations_migrated": result.observations_migrated,
            "errors": result.errors,
            "json_backup_path": result.json_backup_path
        }
        print(json.dumps(output, indent=2))
        sys.exit(0 if result.success else 1)

    # Create KnowledgeGraph instance
    kg = KnowledgeGraph(path=args.path, backend=args.backend)

    output: Any = None

    try:
        if args.command == "create-entities":
            entities_data = json.loads(args.entities)
            created = kg.create_entities(entities_data)
            output = {"created": created, "count": len(created)}

        elif args.command == "create-relations":
            relations_data = json.loads(args.relations)
            created = kg.create_relations(relations_data)
            output = {"created": created, "count": len(created)}

        elif args.command == "add-observations":
            observations = json.loads(args.observations)
            added = kg.add_observations(args.entity, observations)
            output = {"entity": args.entity, "added": added, "count": len(added)}

        elif args.command == "query":
            results = kg.query(
                pattern=args.pattern,
                entity_type=args.entity_type,
                related_to=args.related_to,
                created_after=getattr(args, 'created_after', None),
                created_before=getattr(args, 'created_before', None)
            )
            output = {
                "entities": [e.to_dict() for e in results],
                "count": len(results)
            }

        elif args.command == "get":
            entity_data = kg.get_with_relations(args.entity)
            if entity_data:
                output = entity_data
            else:
                output = {"error": f"Entity '{args.entity}' not found"}
                print(json.dumps(output, indent=2))
                sys.exit(1)

        elif args.command == "list":
            entities = kg.list_entities()
            output = {"entities": entities, "count": len(entities)}

        elif args.command == "delete-entity":
            if kg.delete(args.entity):
                output = {"deleted": args.entity, "success": True}
            else:
                output = {"error": f"Entity '{args.entity}' not found"}
                print(json.dumps(output, indent=2))
                sys.exit(1)

        elif args.command == "export-mermaid":
            mermaid = kg.export_mermaid(
                root=args.root,
                direction=args.direction,
                include_styling=not args.no_styling
            )
            print(mermaid)
            return

        elif args.command == "clear":
            kg.clear()
            output = {"cleared": True, "success": True}

        elif args.command == "search":
            fields = args.fields.split(",") if args.fields else None
            results = kg.search(args.query, fields)
            output = {
                "entities": [e.to_dict() for e in results],
                "count": len(results),
                "query": args.query
            }

        elif args.command == "shortest-path":
            path = kg.shortest_path(args.source, args.target)
            if path:
                output = {"path": path, "length": len(path) - 1}
            else:
                output = {
                    "path": None,
                    "error": f"No path found between '{args.source}' and '{args.target}'"
                }

        elif args.command == "subgraph":
            entity_names, relations = kg.extract_subgraph(args.root, args.depth)
            output = {
                "root": args.root,
                "depth": args.depth,
                "entities": entity_names,
                "relations": [r.to_dict() for r in relations],
                "entity_count": len(entity_names),
                "relation_count": len(relations)
            }

        elif args.command == "export-graphml":
            graphml = kg.export_graphml()
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(graphml)
                output = {"exported": args.output}
            else:
                print(graphml)
                return

        elif args.command == "export-dot":
            dot = kg.export_dot(rankdir=args.direction)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(dot)
                output = {"exported": args.output}
            else:
                print(dot)
                return

        elif args.command == "visualize":
            viz = FigmaVisualizer(kg)
            diagram_data = viz.prepare_workflow_diagram(
                root_entity=args.root,
                depth=args.depth,
                title=args.title
            )

            if args.json:
                output = diagram_data
            else:
                print(FigmaVisualizer.format_cli_output(diagram_data))
                return

        elif args.command == "stats":
            output = kg.get_stats()

        if output is not None:
            print(json.dumps(output, indent=2))

    finally:
        kg.close()


if __name__ == "__main__":
    main()
