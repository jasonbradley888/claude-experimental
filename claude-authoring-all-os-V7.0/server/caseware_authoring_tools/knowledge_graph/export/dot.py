"""DOT/Graphviz export for the Knowledge Graph."""

from typing import Dict, List, Optional

from ..core.models import Entity, Relation


# Shape mapping for DOT format
DOT_SHAPES = {
    "workflow": "ellipse",
    "task": "box",
    "tool": "parallelogram",
    "document": "cylinder",
    "outcome": "circle",
    "finding": "hexagon",
    "risk": "diamond",
    "checklist": "cylinder",
    "evidence": "cylinder",
    "control": "parallelogram",
    "trace": "parallelogram",
}

# Color mapping (DOT uses X11 color names or hex)
DOT_COLORS = {
    "workflow": "royalblue",
    "task": "limegreen",
    "tool": "mediumpurple",
    "document": "orange",
    "outcome": "gold",
    "finding": "tomato",
    "risk": "crimson",
    "checklist": "lightseagreen",
    "evidence": "skyblue",
    "control": "plum",
    "trace": "darkgray",
}

# Edge style mapping
DOT_EDGE_STYLES = {
    "contains": "solid",
    "precedes": "dashed",
    "uses": "dotted",
    "processes": "solid",
    "produces": "bold",
    "leads_to": "solid",
    "mitigates": "dashed",
    "supports": "solid",
    "references": "dotted",
}


def _escape_dot_string(s: str) -> str:
    """Escape special characters for DOT labels."""
    return s.replace('"', '\\"').replace('\n', '\\n')


def _sanitize_id(name: str) -> str:
    """Create a valid DOT node ID from entity name."""
    # Replace characters that aren't valid in DOT IDs
    return name.replace("-", "_").replace(":", "_").replace(" ", "_")


def export_dot(
    entities: List[Entity],
    relations: List[Relation],
    graph_name: str = "KnowledgeGraph",
    rankdir: str = "LR",
    include_styling: bool = True,
    include_observations: bool = False
) -> str:
    """Export knowledge graph as DOT format.

    DOT is the format used by Graphviz and can be rendered to various
    image formats (PNG, SVG, PDF) using tools like:
    - dot
    - neato
    - fdp

    Args:
        entities: List of Entity objects
        relations: List of Relation objects
        graph_name: Name for the graph
        rankdir: Layout direction (LR, TB, RL, BT)
        include_styling: Whether to include colors and shapes
        include_observations: Whether to include observations in tooltips

    Returns:
        DOT format string
    """
    lines = [f'digraph "{graph_name}" {{']

    # Graph attributes
    lines.append(f'    rankdir={rankdir};')
    lines.append('    node [fontname="Arial"];')
    lines.append('    edge [fontname="Arial", fontsize=10];')
    lines.append('')

    # Build node ID mapping
    node_ids = {e.name: _sanitize_id(e.name) for e in entities}

    # Add nodes
    for entity in entities:
        node_id = node_ids[entity.name]
        label = _escape_dot_string(entity.name)

        attrs = [f'label="{label}"']

        if include_styling:
            shape = DOT_SHAPES.get(entity.type, "box")
            color = DOT_COLORS.get(entity.type, "gray")
            attrs.append(f'shape={shape}')
            attrs.append(f'style=filled')
            attrs.append(f'fillcolor={color}')

        if include_observations and entity.observations:
            tooltip = _escape_dot_string(" | ".join(entity.observations))
            attrs.append(f'tooltip="{tooltip}"')

        attr_str = ", ".join(attrs)
        lines.append(f'    {node_id} [{attr_str}];')

    lines.append('')

    # Add edges
    for rel in relations:
        from_id = node_ids.get(rel.from_entity)
        to_id = node_ids.get(rel.to_entity)

        if from_id and to_id:
            label = _escape_dot_string(rel.relation_type)
            attrs = [f'label="{label}"']

            if include_styling:
                style = DOT_EDGE_STYLES.get(rel.relation_type, "solid")
                attrs.append(f'style={style}')

            attr_str = ", ".join(attrs)
            lines.append(f'    {from_id} -> {to_id} [{attr_str}];')

    lines.append('}')
    return '\n'.join(lines)


def export_dot_subgraph(
    entities: List[Entity],
    relations: List[Relation],
    clusters: Dict[str, List[str]],
    graph_name: str = "KnowledgeGraph",
    rankdir: str = "LR"
) -> str:
    """Export knowledge graph with subgraph clusters.

    Args:
        entities: List of Entity objects
        relations: List of Relation objects
        clusters: Dict mapping cluster name to list of entity names
        graph_name: Name for the graph
        rankdir: Layout direction

    Returns:
        DOT format string with subgraph clusters
    """
    lines = [f'digraph "{graph_name}" {{']
    lines.append(f'    rankdir={rankdir};')
    lines.append('    node [fontname="Arial"];')
    lines.append('    edge [fontname="Arial", fontsize=10];')
    lines.append('')

    # Build entity lookup and node IDs
    entities_dict = {e.name: e for e in entities}
    node_ids = {e.name: _sanitize_id(e.name) for e in entities}

    # Track which entities are in clusters
    clustered = set()
    for entity_names in clusters.values():
        clustered.update(entity_names)

    # Add clustered nodes in subgraphs
    for i, (cluster_name, entity_names) in enumerate(clusters.items()):
        lines.append(f'    subgraph cluster_{i} {{')
        lines.append(f'        label="{_escape_dot_string(cluster_name)}";')
        lines.append('        style=filled;')
        lines.append('        color=lightgrey;')

        for name in entity_names:
            if name in entities_dict:
                entity = entities_dict[name]
                node_id = node_ids[name]
                label = _escape_dot_string(name)
                shape = DOT_SHAPES.get(entity.type, "box")
                color = DOT_COLORS.get(entity.type, "gray")
                lines.append(f'        {node_id} [label="{label}", shape={shape}, style=filled, fillcolor={color}];')

        lines.append('    }')
        lines.append('')

    # Add unclustered nodes
    for entity in entities:
        if entity.name not in clustered:
            node_id = node_ids[entity.name]
            label = _escape_dot_string(entity.name)
            shape = DOT_SHAPES.get(entity.type, "box")
            color = DOT_COLORS.get(entity.type, "gray")
            lines.append(f'    {node_id} [label="{label}", shape={shape}, style=filled, fillcolor={color}];')

    lines.append('')

    # Add edges
    for rel in relations:
        from_id = node_ids.get(rel.from_entity)
        to_id = node_ids.get(rel.to_entity)

        if from_id and to_id:
            label = _escape_dot_string(rel.relation_type)
            style = DOT_EDGE_STYLES.get(rel.relation_type, "solid")
            lines.append(f'    {from_id} -> {to_id} [label="{label}", style={style}];')

    lines.append('}')
    return '\n'.join(lines)


def save_dot(
    entities: List[Entity],
    relations: List[Relation],
    path: str,
    **kwargs
) -> None:
    """Save knowledge graph as DOT file.

    Args:
        entities: List of Entity objects
        relations: List of Relation objects
        path: Output file path
        **kwargs: Additional arguments passed to export_dot
    """
    dot_str = export_dot(entities, relations, **kwargs)
    with open(path, "w", encoding="utf-8") as f:
        f.write(dot_str)
