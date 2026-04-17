"""Figma MCP integration for knowledge graph visualization."""

import json
from typing import Optional

from ..core.graph import KnowledgeGraph
from ..export.mermaid import export_mermaid as _export_mermaid, get_mermaid_stats


class FigmaVisualizer:
    """Generate Figma diagrams from knowledge graph data.

    This class prepares Mermaid syntax and metadata for the Figma MCP
    generate_diagram tool. It does not directly call the MCP - that should
    be done by the calling agent using the prepared data.

    Usage:
        from knowledge_graph import KnowledgeGraph
        from knowledge_graph.visualize import FigmaVisualizer

        kg = KnowledgeGraph()
        viz = FigmaVisualizer(kg)

        # Get diagram data for Figma MCP
        result = viz.prepare_workflow_diagram("AA_W_20260123")

        # The result contains:
        # - mermaid: Mermaid syntax to pass to generate_diagram
        # - name: Suggested diagram title
        # - user_intent: Description for the tool
        # - stats: Node/edge counts

        # Then call Figma MCP with:
        # mcp__figma__generate_diagram(
        #     name=result["name"],
        #     mermaidSyntax=result["mermaid"],
        #     userIntent=result["user_intent"]
        # )
    """

    def __init__(self, kg: KnowledgeGraph):
        """Initialize visualizer with a KnowledgeGraph instance.

        Args:
            kg: KnowledgeGraph instance to visualize
        """
        self.kg = kg

    def prepare_workflow_diagram(
        self,
        root_entity: str,
        depth: int = 3,
        title: Optional[str] = None,
        direction: str = "LR"
    ) -> dict:
        """Prepare Mermaid diagram data for Figma MCP.

        Args:
            root_entity: Root entity to start visualization from
            depth: Maximum depth to traverse (default 3)
            title: Optional diagram title (defaults to entity name)
            direction: Diagram direction (LR, TB, RL, BT)

        Returns:
            Dict with:
            - mermaid: Mermaid syntax string
            - name: Diagram title
            - user_intent: Description for Figma MCP
            - stats: Dict with node_count, edge_count, entity_types
            - root: The root entity used
        """
        # Extract subgraph around root
        entity_names, subgraph_relations = self.kg.extract_subgraph(root_entity, depth)

        if not entity_names:
            return {
                "mermaid": f"flowchart {direction}\n    %% Entity not found: {root_entity}",
                "name": title or f"Knowledge Graph: {root_entity}",
                "user_intent": f"Visualize knowledge graph for {root_entity}",
                "stats": {"node_count": 0, "edge_count": 0, "entity_types": {}},
                "root": root_entity,
                "error": f"Entity not found: {root_entity}"
            }

        # Get full entity objects for the subgraph
        entities = [self.kg.get(name) for name in entity_names if self.kg.get(name)]

        # Generate Mermaid without styling (Figma handles styling)
        mermaid = _export_mermaid(
            entities,
            subgraph_relations,
            root=None,  # Already filtered
            direction=direction,
            include_styling=False  # Figma adds its own styling
        )

        # Get stats
        stats = get_mermaid_stats(entities, subgraph_relations)

        # Build diagram name
        name = title or f"Knowledge Graph: {root_entity}"

        return {
            "mermaid": mermaid,
            "name": name,
            "user_intent": f"Visualize knowledge graph workflow starting from {root_entity}",
            "stats": stats,
            "root": root_entity
        }

    def prepare_full_graph_diagram(
        self,
        title: str = "Knowledge Graph",
        direction: str = "LR",
        max_nodes: int = 100
    ) -> dict:
        """Prepare full graph diagram for Figma MCP.

        Args:
            title: Diagram title
            direction: Diagram direction
            max_nodes: Maximum nodes to include (for large graphs)

        Returns:
            Dict with mermaid, name, user_intent, stats
        """
        entities, relations = self.kg._get_graph_data()

        # Warn if graph is too large
        warning = None
        if len(entities) > max_nodes:
            warning = f"Graph has {len(entities)} nodes, truncating to {max_nodes}"
            entities = entities[:max_nodes]
            entity_names = {e.name for e in entities}
            relations = [r for r in relations
                        if r.from_entity in entity_names and r.to_entity in entity_names]

        mermaid = _export_mermaid(
            entities,
            relations,
            direction=direction,
            include_styling=False
        )

        stats = get_mermaid_stats(entities, relations)

        result = {
            "mermaid": mermaid,
            "name": title,
            "user_intent": "Visualize complete knowledge graph",
            "stats": stats
        }

        if warning:
            result["warning"] = warning

        return result

    def prepare_entity_type_diagram(
        self,
        entity_type: str,
        title: Optional[str] = None,
        direction: str = "LR"
    ) -> dict:
        """Prepare diagram showing only entities of a specific type.

        Args:
            entity_type: Type of entities to include (workflow, task, etc.)
            title: Optional diagram title
            direction: Diagram direction

        Returns:
            Dict with mermaid, name, user_intent, stats
        """
        # Query entities of this type
        type_entities = self.kg.query(entity_type=entity_type)

        if not type_entities:
            return {
                "mermaid": f"flowchart {direction}\n    %% No entities of type: {entity_type}",
                "name": title or f"{entity_type.title()} Entities",
                "user_intent": f"Visualize {entity_type} entities",
                "stats": {"node_count": 0, "edge_count": 0, "entity_types": {}},
                "error": f"No entities of type: {entity_type}"
            }

        # Get relations between these entities
        entity_names = {e.name for e in type_entities}
        _, all_relations = self.kg._get_graph_data()
        type_relations = [
            r for r in all_relations
            if r.from_entity in entity_names and r.to_entity in entity_names
        ]

        mermaid = _export_mermaid(
            type_entities,
            type_relations,
            direction=direction,
            include_styling=False
        )

        stats = get_mermaid_stats(type_entities, type_relations)

        return {
            "mermaid": mermaid,
            "name": title or f"{entity_type.title()} Entities",
            "user_intent": f"Visualize all {entity_type} entities and their relations",
            "stats": stats
        }

    @staticmethod
    def get_figma_call_template(diagram_data: dict) -> dict:
        """Get template for Figma MCP tool call.

        Args:
            diagram_data: Result from prepare_* methods

        Returns:
            Dict formatted for mcp__figma__generate_diagram call
        """
        return {
            "name": diagram_data["name"],
            "mermaidSyntax": diagram_data["mermaid"],
            "userIntent": diagram_data["user_intent"]
        }

    @staticmethod
    def format_cli_output(diagram_data: dict) -> str:
        """Format diagram data for CLI output.

        Args:
            diagram_data: Result from prepare_* methods

        Returns:
            Formatted string for CLI display
        """
        lines = [
            f"Diagram: {diagram_data['name']}",
            f"Nodes: {diagram_data['stats']['node_count']}",
            f"Edges: {diagram_data['stats']['edge_count']}",
            ""
        ]

        if diagram_data['stats'].get('entity_types'):
            lines.append("Entity Types:")
            for t, count in diagram_data['stats']['entity_types'].items():
                lines.append(f"  {t}: {count}")
            lines.append("")

        if diagram_data.get('warning'):
            lines.append(f"WARNING: {diagram_data['warning']}")
            lines.append("")

        if diagram_data.get('error'):
            lines.append(f"ERROR: {diagram_data['error']}")
            lines.append("")

        lines.append("Mermaid Syntax:")
        lines.append("-" * 40)
        lines.append(diagram_data['mermaid'])
        lines.append("-" * 40)
        lines.append("")
        lines.append("To generate Figma diagram, use:")
        lines.append("  mcp__figma__generate_diagram with the above mermaid syntax")
        lines.append("")
        lines.append("WARNING: Figma diagrams are ephemeral - save immediately!")

        return "\n".join(lines)
