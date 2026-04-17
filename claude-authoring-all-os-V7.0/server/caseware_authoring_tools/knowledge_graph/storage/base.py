"""Abstract base class for storage backends."""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from ..core.models import Entity, Relation, QueryFilter


class StorageBackend(ABC):
    """Abstract interface for knowledge graph storage backends.

    All storage implementations (JSON, SQLite, etc.) must implement this interface.
    """

    @abstractmethod
    def create_entities(self, entities: List[Entity]) -> List[str]:
        """Create or update multiple entities.

        Args:
            entities: List of Entity objects to create

        Returns:
            List of entity names that were created or updated
        """
        pass

    @abstractmethod
    def create_relations(self, relations: List[Relation]) -> List[str]:
        """Create multiple relations.

        Args:
            relations: List of Relation objects to create

        Returns:
            List of relation descriptions that were created
        """
        pass

    @abstractmethod
    def add_observations(self, entity_name: str, observations: List[str]) -> List[str]:
        """Add observations to an entity.

        If the entity doesn't exist, it will be auto-created with type "unknown".

        Args:
            entity_name: Name of the entity
            observations: List of observation strings to add

        Returns:
            List of observations that were added (excluding duplicates)
        """
        pass

    @abstractmethod
    def query(self, filter: QueryFilter) -> List[Entity]:
        """Query entities matching the filter criteria.

        Args:
            filter: QueryFilter with criteria (pattern, type, related_to, etc.)

        Returns:
            List of matching Entity objects
        """
        pass

    @abstractmethod
    def search(self, query: str, fields: Optional[List[str]] = None) -> List[Entity]:
        """Full-text search across entities.

        Args:
            query: Search query string
            fields: Optional list of fields to search (name, type, observations)

        Returns:
            List of matching Entity objects
        """
        pass

    @abstractmethod
    def get(self, entity_name: str) -> Optional[Entity]:
        """Get a single entity by name.

        Args:
            entity_name: Name of the entity to retrieve

        Returns:
            Entity object or None if not found
        """
        pass

    @abstractmethod
    def get_with_relations(self, entity_name: str) -> Optional[dict]:
        """Get entity with its incoming and outgoing relations.

        Args:
            entity_name: Name of the entity

        Returns:
            Dict with entity data plus 'incoming_relations' and 'outgoing_relations'
            or None if entity not found
        """
        pass

    @abstractmethod
    def delete(self, entity_name: str) -> bool:
        """Delete an entity and its relations.

        Args:
            entity_name: Name of the entity to delete

        Returns:
            True if entity was deleted, False if not found
        """
        pass

    @abstractmethod
    def list_entities(self) -> List[dict]:
        """List all entities with summary info.

        Returns:
            List of dicts with name, type, observations_count, created_at
        """
        pass

    @abstractmethod
    def get_graph_data(self) -> Tuple[List[Entity], List[Relation]]:
        """Get all entities and relations for graph operations.

        Returns:
            Tuple of (entities list, relations list)
        """
        pass

    @abstractmethod
    def get_relations(self, entity_name: Optional[str] = None) -> List[Relation]:
        """Get relations, optionally filtered by entity involvement.

        Args:
            entity_name: If provided, return only relations involving this entity

        Returns:
            List of Relation objects
        """
        pass

    @abstractmethod
    def clear(self) -> bool:
        """Clear all data from the storage.

        Returns:
            True if cleared successfully
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close any open resources (connections, file handles, etc.)."""
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures resources are closed."""
        self.close()
        return False
