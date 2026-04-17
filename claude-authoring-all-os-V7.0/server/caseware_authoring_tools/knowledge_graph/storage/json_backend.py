"""JSON file-based storage backend for the Knowledge Graph."""

import fnmatch
import json
from pathlib import Path
from typing import List, Optional, Tuple

from ..core.models import Entity, Relation, QueryFilter, get_timestamp
from .base import StorageBackend


class JSONBackend(StorageBackend):
    """JSON file-based storage backend.

    Stores the knowledge graph in a single JSON file with structure:
    {
        "version": "1.0",
        "last_updated": "ISO8601 timestamp",
        "entities": {name: {...}},
        "relations": [{from, type, to, created_at}, ...]
    }
    """

    def __init__(self, path: Path):
        """Initialize JSON backend.

        Args:
            path: Path to the JSON file (will be created if doesn't exist)
        """
        self.path = Path(path)
        self._data = self._load()

    def _load(self) -> dict:
        """Load knowledge graph from JSON file."""
        if not self.path.exists():
            return {
                "version": "1.0",
                "last_updated": get_timestamp(),
                "entities": {},
                "relations": []
            }
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self) -> None:
        """Save knowledge graph to JSON file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data["last_updated"] = get_timestamp()
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def create_entities(self, entities: List[Entity]) -> List[str]:
        """Create or update multiple entities."""
        created = []
        timestamp = get_timestamp()

        for entity in entities:
            name = entity.name
            if name not in self._data["entities"]:
                self._data["entities"][name] = {
                    "name": name,
                    "type": entity.type,
                    "observations": entity.observations.copy(),
                    "created_at": timestamp
                }
                created.append(name)
            else:
                # Update existing entity
                self._data["entities"][name]["type"] = entity.type
                for obs in entity.observations:
                    if obs not in self._data["entities"][name]["observations"]:
                        self._data["entities"][name]["observations"].append(obs)
                created.append(f"{name} (updated)")

        self._save()
        return created

    def create_relations(self, relations: List[Relation]) -> List[str]:
        """Create multiple relations."""
        created = []
        timestamp = get_timestamp()

        for rel in relations:
            # Check if relation already exists
            exists = any(
                r["from"] == rel.from_entity and
                r["type"] == rel.relation_type and
                r["to"] == rel.to_entity
                for r in self._data["relations"]
            )

            if not exists:
                self._data["relations"].append({
                    "from": rel.from_entity,
                    "type": rel.relation_type,
                    "to": rel.to_entity,
                    "created_at": timestamp
                })
                created.append(f"{rel.from_entity} --{rel.relation_type}--> {rel.to_entity}")

        self._save()
        return created

    def add_observations(self, entity_name: str, observations: List[str]) -> List[str]:
        """Add observations to an entity."""
        added = []

        if entity_name not in self._data["entities"]:
            # Auto-create entity
            self._data["entities"][entity_name] = {
                "name": entity_name,
                "type": "unknown",
                "observations": [],
                "created_at": get_timestamp()
            }

        for obs in observations:
            if obs not in self._data["entities"][entity_name]["observations"]:
                self._data["entities"][entity_name]["observations"].append(obs)
                added.append(obs)

        self._save()
        return added

    def query(self, filter: QueryFilter) -> List[Entity]:
        """Query entities matching filter criteria."""
        results = []

        for name, data in self._data["entities"].items():
            include = True

            # Filter by glob pattern
            if filter.pattern and not fnmatch.fnmatch(name, filter.pattern):
                include = False

            # Filter by type
            if filter.entity_type and data.get("type") != filter.entity_type:
                include = False

            # Filter by relation
            if filter.related_to:
                related = any(
                    r["from"] == filter.related_to and r["to"] == name or
                    r["to"] == filter.related_to and r["from"] == name
                    for r in self._data["relations"]
                )
                if not related:
                    include = False

            # Filter by created_after
            if filter.created_after and data.get("created_at", "") < filter.created_after:
                include = False

            # Filter by created_before
            if filter.created_before and data.get("created_at", "") > filter.created_before:
                include = False

            if include:
                results.append(Entity.from_dict(data))

        return results

    def search(self, query: str, fields: Optional[List[str]] = None) -> List[Entity]:
        """Full-text search across entities."""
        if fields is None:
            fields = ["name", "type", "observations"]

        query_lower = query.lower()
        results = []

        for name, data in self._data["entities"].items():
            matched = False

            if "name" in fields and query_lower in name.lower():
                matched = True
            if "type" in fields and query_lower in data.get("type", "").lower():
                matched = True
            if "observations" in fields:
                for obs in data.get("observations", []):
                    if query_lower in obs.lower():
                        matched = True
                        break

            if matched:
                results.append(Entity.from_dict(data))

        return results

    def get(self, entity_name: str) -> Optional[Entity]:
        """Get a single entity by name."""
        if entity_name not in self._data["entities"]:
            return None
        return Entity.from_dict(self._data["entities"][entity_name])

    def get_with_relations(self, entity_name: str) -> Optional[dict]:
        """Get entity with its relations."""
        if entity_name not in self._data["entities"]:
            return None

        entity_data = self._data["entities"][entity_name].copy()

        # Find related relations
        outgoing = [r for r in self._data["relations"] if r["from"] == entity_name]
        incoming = [r for r in self._data["relations"] if r["to"] == entity_name]

        entity_data["outgoing_relations"] = outgoing
        entity_data["incoming_relations"] = incoming

        return entity_data

    def delete(self, entity_name: str) -> bool:
        """Delete an entity and its relations."""
        if entity_name not in self._data["entities"]:
            return False

        del self._data["entities"][entity_name]

        # Remove related relations
        self._data["relations"] = [
            r for r in self._data["relations"]
            if r["from"] != entity_name and r["to"] != entity_name
        ]

        self._save()
        return True

    def list_entities(self) -> List[dict]:
        """List all entities with summary info."""
        return [
            {
                "name": e["name"],
                "type": e["type"],
                "observations_count": len(e.get("observations", [])),
                "created_at": e.get("created_at", "unknown")
            }
            for e in self._data["entities"].values()
        ]

    def get_graph_data(self) -> Tuple[List[Entity], List[Relation]]:
        """Get all entities and relations."""
        entities = [Entity.from_dict(e) for e in self._data["entities"].values()]
        relations = [Relation.from_dict(r) for r in self._data["relations"]]
        return entities, relations

    def get_relations(self, entity_name: Optional[str] = None) -> List[Relation]:
        """Get relations, optionally filtered by entity."""
        if entity_name is None:
            return [Relation.from_dict(r) for r in self._data["relations"]]

        return [
            Relation.from_dict(r) for r in self._data["relations"]
            if r["from"] == entity_name or r["to"] == entity_name
        ]

    def clear(self) -> bool:
        """Clear all data."""
        self._data["entities"] = {}
        self._data["relations"] = []
        self._save()
        return True

    def close(self) -> None:
        """No-op for JSON backend (no persistent connection)."""
        pass

    def get_raw_data(self) -> dict:
        """Get the raw data dict (for migration purposes)."""
        return self._data.copy()
