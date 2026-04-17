"""Core data models for the Knowledge Graph."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


def get_timestamp() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Entity:
    """Represents a node in the knowledge graph.

    Attributes:
        name: Unique identifier following naming convention {AgentCode}_{TypeCode}_{Identifier}
        type: Entity type (workflow, task, document, tool, outcome, finding, risk, etc.)
        observations: List of observation strings attached to this entity
        created_at: ISO 8601 timestamp when entity was created
        updated_at: ISO 8601 timestamp when entity was last updated
    """
    name: str
    type: str
    observations: List[str] = field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = get_timestamp()
        if self.updated_at is None:
            self.updated_at = self.created_at

    def to_dict(self) -> dict:
        """Convert entity to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "type": self.type,
            "observations": self.observations,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Entity":
        """Create entity from dictionary."""
        return cls(
            name=data["name"],
            type=data.get("type", "unknown"),
            observations=data.get("observations", []),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )


@dataclass
class Relation:
    """Represents an edge in the knowledge graph.

    Attributes:
        from_entity: Source entity name
        relation_type: Type of relation (contains, precedes, uses, produces, etc.)
        to_entity: Target entity name
        created_at: ISO 8601 timestamp when relation was created
    """
    from_entity: str
    relation_type: str
    to_entity: str
    created_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = get_timestamp()

    def to_dict(self) -> dict:
        """Convert relation to dictionary for JSON serialization."""
        return {
            "from": self.from_entity,
            "type": self.relation_type,
            "to": self.to_entity,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Relation":
        """Create relation from dictionary."""
        return cls(
            from_entity=data["from"],
            relation_type=data["type"],
            to_entity=data["to"],
            created_at=data.get("created_at")
        )


@dataclass
class QueryFilter:
    """Filter criteria for querying entities.

    Attributes:
        pattern: Glob pattern to match entity names (e.g., "AA_T_*")
        entity_type: Filter by entity type (workflow, task, etc.)
        related_to: Find entities connected to this entity
        created_after: ISO 8601 timestamp, include entities created after this time
        created_before: ISO 8601 timestamp, include entities created before this time
        search_text: Full-text search query
        search_fields: Fields to search in (name, type, observations)
    """
    pattern: Optional[str] = None
    entity_type: Optional[str] = None
    related_to: Optional[str] = None
    created_after: Optional[str] = None
    created_before: Optional[str] = None
    search_text: Optional[str] = None
    search_fields: Optional[List[str]] = None

    def is_empty(self) -> bool:
        """Check if filter has any criteria set."""
        return all(
            getattr(self, f) is None
            for f in ["pattern", "entity_type", "related_to",
                      "created_after", "created_before", "search_text"]
        )


@dataclass
class MigrationResult:
    """Result of a JSON to SQLite migration.

    Attributes:
        success: Whether migration completed successfully
        entities_migrated: Number of entities migrated
        relations_migrated: Number of relations migrated
        observations_migrated: Number of observations migrated
        errors: List of error messages if any
        json_backup_path: Path where JSON file was backed up
    """
    success: bool
    entities_migrated: int = 0
    relations_migrated: int = 0
    observations_migrated: int = 0
    errors: List[str] = field(default_factory=list)
    json_backup_path: Optional[str] = None


# Standard entity types used in the knowledge graph
ENTITY_TYPES = {
    "workflow": "Workflow orchestration entity",
    "task": "Individual task within a workflow",
    "document": "Document being processed or produced",
    "tool": "MCP tool or utility used in processing",
    "outcome": "Result or output of a workflow",
    "finding": "Discovery or observation from analysis",
    "risk": "Identified risk or concern",
    "checklist": "Checklist document type",
    "evidence": "Supporting evidence document",
    "control": "Control or mitigation measure",
    "trace": "MCP tool call trace entity"
}

# Standard relation types
RELATION_TYPES = {
    "contains": "Workflow/group includes this entity",
    "precedes": "Sequential ordering (A before B)",
    "uses": "Task utilizes tool",
    "processes": "Task reads/analyzes document",
    "produces": "Task creates document/outcome",
    "leads_to": "Contributes to result",
    "mitigates": "Control addresses risk",
    "supports": "Evidence substantiates finding",
    "references": "General reference link"
}
