"""Main KnowledgeGraph class that wraps storage backends and provides unified API."""

from pathlib import Path
from typing import List, Optional, Set, Tuple, Union

from .models import Entity, Relation, QueryFilter, MigrationResult
from ..storage.base import StorageBackend
from ..storage.json_backend import JSONBackend
from ..storage.sqlite_backend import SQLiteBackend
from ..storage.migration import migrate_json_to_sqlite, get_default_paths
from ..algorithms.traversal import (
    shortest_path as _shortest_path,
    all_paths as _all_paths,
    connected_components as _connected_components,
    extract_subgraph as _extract_subgraph,
    get_descendants as _get_descendants,
    get_ancestors as _get_ancestors,
    topological_sort as _topological_sort,
    build_networkx_graph
)
from ..export.mermaid import export_mermaid as _export_mermaid, get_mermaid_stats
from ..export.graphml import export_graphml as _export_graphml
from ..export.dot import export_dot as _export_dot


class KnowledgeGraph:
    """Main interface for the Knowledge Graph.

    Provides a unified API for:
    - Creating/querying entities and relations
    - Full-text search
    - Graph algorithms (shortest path, connected components, etc.)
    - Export to various formats (Mermaid, GraphML, DOT)

    Usage:
        # Create with SQLite backend (default)
        kg = KnowledgeGraph()

        # Create with JSON backend
        kg = KnowledgeGraph(backend="json")

        # Create with specific path
        kg = KnowledgeGraph(path="/path/to/db.sqlite")

        # Use as context manager
        with KnowledgeGraph() as kg:
            kg.create_entities([...])
    """

    def __init__(
        self,
        path: Optional[Union[str, Path]] = None,
        backend: str = "sqlite"
    ):
        """Initialize KnowledgeGraph.

        Args:
            path: Path to storage file. If None, uses default location.
            backend: Storage backend type ("sqlite" or "json")
        """
        self.backend_type = backend

        if path is None:
            json_default, sqlite_default = get_default_paths()
            path = sqlite_default if backend == "sqlite" else json_default

        self.path = Path(path)
        self._backend = self._create_backend(self.path, backend)

    def _create_backend(self, path: Path, backend: str) -> StorageBackend:
        """Create the appropriate storage backend."""
        if backend == "sqlite":
            return SQLiteBackend(path)
        elif backend == "json":
            return JSONBackend(path)
        else:
            raise ValueError(f"Unknown backend: {backend}. Use 'sqlite' or 'json'.")

    # -------------------------------------------------------------------------
    # Core CRUD Operations
    # -------------------------------------------------------------------------

    def create_entities(self, entities: List[Union[Entity, dict]]) -> List[str]:
        """Create or update multiple entities.

        Args:
            entities: List of Entity objects or dicts with name, type, observations

        Returns:
            List of entity names that were created/updated
        """
        entity_objs = []
        for e in entities:
            if isinstance(e, dict):
                entity_objs.append(Entity(
                    name=e["name"],
                    type=e.get("type", "unknown"),
                    observations=e.get("observations", [])
                ))
            else:
                entity_objs.append(e)

        return self._backend.create_entities(entity_objs)

    def create_relations(self, relations: List[Union[Relation, list, tuple]]) -> List[str]:
        """Create multiple relations.

        Args:
            relations: List of Relation objects or [from, type, to] tuples

        Returns:
            List of relation descriptions that were created
        """
        relation_objs = []
        for r in relations:
            if isinstance(r, (list, tuple)):
                relation_objs.append(Relation(
                    from_entity=r[0],
                    relation_type=r[1],
                    to_entity=r[2]
                ))
            else:
                relation_objs.append(r)

        return self._backend.create_relations(relation_objs)

    def add_observations(self, entity_name: str, observations: List[str]) -> List[str]:
        """Add observations to an entity.

        If entity doesn't exist, it will be auto-created.

        Args:
            entity_name: Name of the entity
            observations: List of observation strings

        Returns:
            List of observations that were added
        """
        return self._backend.add_observations(entity_name, observations)

    def query(
        self,
        pattern: Optional[str] = None,
        entity_type: Optional[str] = None,
        related_to: Optional[str] = None,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
        **kwargs
    ) -> List[Entity]:
        """Query entities by various criteria.

        Args:
            pattern: Glob pattern to match entity names (e.g., "AA_T_*")
            entity_type: Filter by entity type
            related_to: Find entities connected to this entity
            created_after: ISO 8601 timestamp
            created_before: ISO 8601 timestamp

        Returns:
            List of matching Entity objects
        """
        filter = QueryFilter(
            pattern=pattern,
            entity_type=entity_type,
            related_to=related_to,
            created_after=created_after,
            created_before=created_before
        )
        return self._backend.query(filter)

    def search(self, query: str, fields: Optional[List[str]] = None) -> List[Entity]:
        """Full-text search across entities.

        Args:
            query: Search query string
            fields: Fields to search (name, type, observations). Defaults to all.

        Returns:
            List of matching Entity objects
        """
        return self._backend.search(query, fields)

    def get(self, entity_name: str) -> Optional[Entity]:
        """Get a single entity by name.

        Args:
            entity_name: Name of the entity

        Returns:
            Entity object or None if not found
        """
        return self._backend.get(entity_name)

    def get_with_relations(self, entity_name: str) -> Optional[dict]:
        """Get entity with its incoming and outgoing relations.

        Args:
            entity_name: Name of the entity

        Returns:
            Dict with entity data plus incoming_relations and outgoing_relations
        """
        return self._backend.get_with_relations(entity_name)

    def delete(self, entity_name: str) -> bool:
        """Delete an entity and its relations.

        Args:
            entity_name: Name of the entity to delete

        Returns:
            True if deleted, False if not found
        """
        return self._backend.delete(entity_name)

    def list_entities(self) -> List[dict]:
        """List all entities with summary info.

        Returns:
            List of dicts with name, type, observations_count, created_at
        """
        return self._backend.list_entities()

    def clear(self) -> bool:
        """Clear all data from the knowledge graph.

        Returns:
            True if cleared successfully
        """
        return self._backend.clear()

    # -------------------------------------------------------------------------
    # Graph Algorithms
    # -------------------------------------------------------------------------

    def _get_graph_data(self) -> Tuple[List[Entity], List[Relation]]:
        """Get all entities and relations for graph operations."""
        return self._backend.get_graph_data()

    def shortest_path(self, source: str, target: str) -> Optional[List[str]]:
        """Find shortest path between two entities.

        Args:
            source: Source entity name
            target: Target entity name

        Returns:
            List of entity names in path, or None if no path exists
        """
        entities, relations = self._get_graph_data()
        return _shortest_path(entities, relations, source, target)

    def all_paths(
        self,
        source: str,
        target: str,
        max_depth: int = 10
    ) -> List[List[str]]:
        """Find all paths between two entities.

        Args:
            source: Source entity name
            target: Target entity name
            max_depth: Maximum path length

        Returns:
            List of paths
        """
        entities, relations = self._get_graph_data()
        return _all_paths(entities, relations, source, target, max_depth)

    def connected_components(self) -> List[Set[str]]:
        """Find connected components in the graph.

        Returns:
            List of sets, each containing entity names in a component
        """
        entities, relations = self._get_graph_data()
        return _connected_components(entities, relations)

    def extract_subgraph(
        self,
        root: str,
        depth: int = 3
    ) -> Tuple[List[str], List[Relation]]:
        """Extract subgraph centered on root entity.

        Args:
            root: Root entity name
            depth: Maximum depth to traverse

        Returns:
            Tuple of (entity names, relations in subgraph)
        """
        entities, relations = self._get_graph_data()
        return _extract_subgraph(entities, relations, root, depth)

    def get_descendants(self, root: str) -> Set[str]:
        """Get all descendants reachable from root via outgoing edges.

        Args:
            root: Root entity name

        Returns:
            Set of descendant entity names
        """
        entities, relations = self._get_graph_data()
        return _get_descendants(entities, relations, root)

    def get_ancestors(self, target: str) -> Set[str]:
        """Get all ancestors that can reach target via outgoing edges.

        Args:
            target: Target entity name

        Returns:
            Set of ancestor entity names
        """
        entities, relations = self._get_graph_data()
        return _get_ancestors(entities, relations, target)

    def topological_sort(self) -> Optional[List[str]]:
        """Return topological ordering if graph is a DAG.

        Returns:
            List of entity names in topological order, or None if cycles exist
        """
        entities, relations = self._get_graph_data()
        return _topological_sort(entities, relations)

    # -------------------------------------------------------------------------
    # Export Methods
    # -------------------------------------------------------------------------

    def export_mermaid(
        self,
        root: Optional[str] = None,
        direction: str = "LR",
        include_styling: bool = True
    ) -> str:
        """Export graph as Mermaid diagram.

        Args:
            root: Optional root entity to limit scope
            direction: Graph direction (LR, TB, RL, BT)
            include_styling: Include color styling

        Returns:
            Mermaid diagram string
        """
        entities, relations = self._get_graph_data()
        return _export_mermaid(entities, relations, root, direction, include_styling)

    def export_graphml(self, include_observations: bool = True) -> str:
        """Export graph as GraphML XML.

        Args:
            include_observations: Include observations in export

        Returns:
            GraphML XML string
        """
        entities, relations = self._get_graph_data()
        return _export_graphml(entities, relations, include_observations)

    def export_dot(
        self,
        graph_name: str = "KnowledgeGraph",
        rankdir: str = "LR",
        include_styling: bool = True
    ) -> str:
        """Export graph as DOT/Graphviz format.

        Args:
            graph_name: Name for the graph
            rankdir: Layout direction
            include_styling: Include colors and shapes

        Returns:
            DOT format string
        """
        entities, relations = self._get_graph_data()
        return _export_dot(entities, relations, graph_name, rankdir, include_styling)

    def get_mermaid_stats(self, root: Optional[str] = None) -> dict:
        """Get statistics about Mermaid diagram.

        Args:
            root: Optional root entity

        Returns:
            Dict with node_count, edge_count, entity_types
        """
        entities, relations = self._get_graph_data()
        return get_mermaid_stats(entities, relations, root)

    # -------------------------------------------------------------------------
    # Migration
    # -------------------------------------------------------------------------

    @staticmethod
    def migrate_to_sqlite(
        json_path: Optional[Union[str, Path]] = None,
        sqlite_path: Optional[Union[str, Path]] = None,
        backup_json: bool = True
    ) -> MigrationResult:
        """Migrate data from JSON to SQLite backend.

        Args:
            json_path: Source JSON file path (default: tracing/knowledge_graph.json)
            sqlite_path: Destination SQLite path (default: tracing/knowledge_graph.db)
            backup_json: Whether to backup JSON file

        Returns:
            MigrationResult with statistics
        """
        json_default, sqlite_default = get_default_paths()

        if json_path is None:
            json_path = json_default
        if sqlite_path is None:
            sqlite_path = sqlite_default

        return migrate_json_to_sqlite(
            Path(json_path),
            Path(sqlite_path),
            backup_json
        )

    # -------------------------------------------------------------------------
    # Context Manager and Utilities
    # -------------------------------------------------------------------------

    def close(self) -> None:
        """Close the storage backend."""
        self._backend.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False

    def get_stats(self) -> dict:
        """Get storage statistics.

        Returns:
            Dict with entity, relation, and observation counts
        """
        entities, relations = self._get_graph_data()
        total_observations = sum(len(e.observations) for e in entities)

        return {
            "entities": len(entities),
            "relations": len(relations),
            "observations": total_observations,
            "backend": self.backend_type,
            "path": str(self.path)
        }
