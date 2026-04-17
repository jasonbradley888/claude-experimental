"""Mermaid diagram export for the Knowledge Graph."""

from typing import Dict, List, Optional, Set

from ..core.models import Entity, Relation


# Define node shapes by entity type
TYPE_SHAPES = {
    "workflow": ('([', '])'),      # Stadium/pill
    "task": ('[', ']'),             # Rectangle
    "tool": ('[/', '/]'),           # Parallelogram
    "document": ('[(', ')]'),       # Cylindrical
    "outcome": ('((', '))'),        # Circle
    "finding": ('{{', '}}'),        # Hexagon
    "risk": ('{', '}'),             # Rhombus
    "checklist": ('[(', ')]'),      # Cylindrical
    "evidence": ('[(', ')]'),       # Cylindrical
    "control": ('[/', '/]'),        # Parallelogram
    "trace": ('[/', '/]'),          # Parallelogram
}

# Define type colors
TYPE_COLORS = {
    "workflow": "#4169E1",    # Royal Blue
    "task": "#32CD32",        # Lime Green
    "tool": "#9370DB",        # Medium Purple
    "document": "#FFA500",    # Orange
    "outcome": "#FFD700",     # Gold
    "finding": "#FF6347",     # Tomato
    "risk": "#DC143C",        # Crimson
    "checklist": "#20B2AA",   # Light Sea Green
    "evidence": "#87CEEB",    # Sky Blue
    "control": "#DDA0DD",     # Plum
    "trace": "#A9A9A9",       # Dark Gray
}

# Relation line styles
RELATION_STYLES = {
    "contains": "-->",
    "precedes": "-.->",
    "uses": "-.-",
    "processes": "---",
    "produces": "==>",
    "leads_to": "-->",
    "mitigates": "-.->",
    "supports": "---",
    "references": "-.-",
}


def _get_connected_entities(
    root: str,
    entities: Dict[str, Entity],
    relations: List[Relation]
) -> Set[str]:
    """Get all entities connected to root using BFS."""
    connected = {root}
    queue = [root]

    while queue:
        current = queue.pop(0)
        for rel in relations:
            if rel.from_entity == current and rel.to_entity not in connected:
                connected.add(rel.to_entity)
                queue.append(rel.to_entity)
            if rel.to_entity == current and rel.from_entity not in connected:
                connected.add(rel.from_entity)
                queue.append(rel.from_entity)

    return connected


def export_mermaid(
    entities: List[Entity],
    relations: List[Relation],
    root: Optional[str] = None,
    direction: str = "LR",
    include_styling: bool = True
) -> str:
    """Export knowledge graph as Mermaid diagram.

    Args:
        entities: List of Entity objects
        relations: List of Relation objects
        root: Optional root entity - if provided, only include connected entities
        direction: Graph direction (LR, TB, RL, BT)
        include_styling: Whether to include color styling

    Returns:
        Mermaid diagram string
    """
    lines = [f"flowchart {direction}"]

    # Build entity dict for lookup
    entities_dict = {e.name: e for e in entities}

    # Filter by root if provided
    if root and root in entities_dict:
        connected = _get_connected_entities(root, entities_dict, relations)
        entities_dict = {k: v for k, v in entities_dict.items() if k in connected}
        relations = [r for r in relations if r.from_entity in connected and r.to_entity in connected]

    if not entities_dict:
        return "flowchart LR\n    %% Empty graph"

    # Generate node definitions
    node_ids = {}
    for i, (name, entity) in enumerate(entities_dict.items()):
        node_id = f"N{i}"
        node_ids[name] = node_id

        entity_type = entity.type
        shape_start, shape_end = TYPE_SHAPES.get(entity_type, ('[', ']'))

        # Escape quotes and create label
        label = name.replace('"', "'")
        lines.append(f"    {node_id}{shape_start}\"{label}\"{shape_end}")

    # Generate relations
    for rel in relations:
        from_id = node_ids.get(rel.from_entity)
        to_id = node_ids.get(rel.to_entity)
        if from_id and to_id:
            arrow = RELATION_STYLES.get(rel.relation_type, "-->")
            label = rel.relation_type
            lines.append(f"    {from_id} {arrow}|\"{label}\"| {to_id}")

    # Add styling
    if include_styling:
        lines.append("")
        for name, entity in entities_dict.items():
            node_id = node_ids.get(name)
            entity_type = entity.type
            color = TYPE_COLORS.get(entity_type, "#808080")
            lines.append(f"    style {node_id} fill:{color}")

    return "\n".join(lines)


def export_mermaid_simple(
    entities: List[Entity],
    relations: List[Relation],
    root: Optional[str] = None
) -> str:
    """Export a simplified Mermaid diagram without styling.

    Useful for Figma MCP which has simpler requirements.

    Args:
        entities: List of Entity objects
        relations: List of Relation objects
        root: Optional root entity

    Returns:
        Simplified Mermaid diagram string
    """
    return export_mermaid(
        entities, relations, root,
        direction="LR",
        include_styling=False
    )


def get_mermaid_stats(
    entities: List[Entity],
    relations: List[Relation],
    root: Optional[str] = None
) -> dict:
    """Get statistics about the Mermaid diagram.

    Args:
        entities: List of Entity objects
        relations: List of Relation objects
        root: Optional root entity

    Returns:
        Dict with node_count, edge_count, entity_types
    """
    entities_dict = {e.name: e for e in entities}

    if root and root in entities_dict:
        connected = _get_connected_entities(root, entities_dict, relations)
        entities_dict = {k: v for k, v in entities_dict.items() if k in connected}
        relations = [r for r in relations if r.from_entity in connected and r.to_entity in connected]

    # Count entity types
    type_counts = {}
    for entity in entities_dict.values():
        t = entity.type
        type_counts[t] = type_counts.get(t, 0) + 1

    return {
        "node_count": len(entities_dict),
        "edge_count": len(relations),
        "entity_types": type_counts
    }
