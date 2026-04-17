"""GraphML export for the Knowledge Graph."""

import xml.etree.ElementTree as ET
from typing import List, Optional

from ..core.models import Entity, Relation


def export_graphml(
    entities: List[Entity],
    relations: List[Relation],
    include_observations: bool = True
) -> str:
    """Export knowledge graph as GraphML.

    GraphML is an XML-based format that can be imported into tools like:
    - Gephi
    - yEd
    - Cytoscape
    - Neo4j

    Args:
        entities: List of Entity objects
        relations: List of Relation objects
        include_observations: Whether to include observations as node attributes

    Returns:
        GraphML XML string
    """
    # Create root element with namespaces
    root = ET.Element("graphml")
    root.set("xmlns", "http://graphml.graphdrawing.org/xmlns")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set("xsi:schemaLocation",
             "http://graphml.graphdrawing.org/xmlns "
             "http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd")

    # Define node attribute keys
    key_type = ET.SubElement(root, "key")
    key_type.set("id", "type")
    key_type.set("for", "node")
    key_type.set("attr.name", "type")
    key_type.set("attr.type", "string")

    key_created = ET.SubElement(root, "key")
    key_created.set("id", "created_at")
    key_created.set("for", "node")
    key_created.set("attr.name", "created_at")
    key_created.set("attr.type", "string")

    if include_observations:
        key_obs = ET.SubElement(root, "key")
        key_obs.set("id", "observations")
        key_obs.set("for", "node")
        key_obs.set("attr.name", "observations")
        key_obs.set("attr.type", "string")

    # Define edge attribute keys
    key_rel_type = ET.SubElement(root, "key")
    key_rel_type.set("id", "relation_type")
    key_rel_type.set("for", "edge")
    key_rel_type.set("attr.name", "relation_type")
    key_rel_type.set("attr.type", "string")

    key_rel_created = ET.SubElement(root, "key")
    key_rel_created.set("id", "edge_created_at")
    key_rel_created.set("for", "edge")
    key_rel_created.set("attr.name", "created_at")
    key_rel_created.set("attr.type", "string")

    # Create graph element
    graph = ET.SubElement(root, "graph")
    graph.set("id", "KnowledgeGraph")
    graph.set("edgedefault", "directed")

    # Add nodes
    for entity in entities:
        node = ET.SubElement(graph, "node")
        node.set("id", entity.name)

        data_type = ET.SubElement(node, "data")
        data_type.set("key", "type")
        data_type.text = entity.type

        if entity.created_at:
            data_created = ET.SubElement(node, "data")
            data_created.set("key", "created_at")
            data_created.text = entity.created_at

        if include_observations and entity.observations:
            data_obs = ET.SubElement(node, "data")
            data_obs.set("key", "observations")
            data_obs.text = " | ".join(entity.observations)

    # Add edges
    for i, rel in enumerate(relations):
        edge = ET.SubElement(graph, "edge")
        edge.set("id", f"e{i}")
        edge.set("source", rel.from_entity)
        edge.set("target", rel.to_entity)

        data_rel_type = ET.SubElement(edge, "data")
        data_rel_type.set("key", "relation_type")
        data_rel_type.text = rel.relation_type

        if rel.created_at:
            data_rel_created = ET.SubElement(edge, "data")
            data_rel_created.set("key", "edge_created_at")
            data_rel_created.text = rel.created_at

    # Convert to string with proper formatting
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def save_graphml(
    entities: List[Entity],
    relations: List[Relation],
    path: str,
    include_observations: bool = True
) -> None:
    """Save knowledge graph as GraphML file.

    Args:
        entities: List of Entity objects
        relations: List of Relation objects
        path: Output file path
        include_observations: Whether to include observations
    """
    xml_str = export_graphml(entities, relations, include_observations)
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml_str)
