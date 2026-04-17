"""
Knowledge Graph Package

A local knowledge graph implementation for tracking authoring workflows.
Provides SQLite backend with FTS5, graph algorithms, and visualization.

Usage:
    from knowledge_graph import KnowledgeGraph, Entity, Relation

    # Create graph instance
    kg = KnowledgeGraph()

    # Create entities
    kg.create_entities([
        Entity(name="AA_W_20260123", type="workflow"),
        Entity(name="AA_T_task1", type="task")
    ])

    # Create relations
    kg.create_relations([
        Relation(from_entity="AA_W_20260123", relation_type="contains", to_entity="AA_T_task1")
    ])

    # Query
    results = kg.query(pattern="AA_T_*")

    # Export
    mermaid = kg.export_mermaid(root="AA_W_20260123")
"""

__version__ = "2.0.0"

from .core import (
    Entity,
    Relation,
    QueryFilter,
    MigrationResult,
    ENTITY_TYPES,
    RELATION_TYPES,
    get_timestamp
)

from .core.graph import KnowledgeGraph

__all__ = [
    # Version
    "__version__",
    # Core models
    "Entity",
    "Relation",
    "QueryFilter",
    "MigrationResult",
    "ENTITY_TYPES",
    "RELATION_TYPES",
    "get_timestamp",
    # Main class
    "KnowledgeGraph",
]
