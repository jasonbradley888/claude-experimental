"""Migration utility for JSON to SQLite conversion."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..core.models import Entity, Relation, MigrationResult
from .json_backend import JSONBackend
from .sqlite_backend import SQLiteBackend


def migrate_json_to_sqlite(
    json_path: Path,
    sqlite_path: Path,
    backup_json: bool = True
) -> MigrationResult:
    """Migrate knowledge graph data from JSON to SQLite.

    Args:
        json_path: Path to source JSON file
        sqlite_path: Path to destination SQLite database
        backup_json: Whether to backup the JSON file after migration

    Returns:
        MigrationResult with migration statistics
    """
    result = MigrationResult(success=False)
    json_path = Path(json_path)
    sqlite_path = Path(sqlite_path)

    # Validate source exists
    if not json_path.exists():
        result.errors.append(f"Source JSON file not found: {json_path}")
        return result

    try:
        # Load JSON data
        json_backend = JSONBackend(json_path)
        raw_data = json_backend.get_raw_data()

        # Create SQLite database
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        sqlite_backend = SQLiteBackend(sqlite_path)

        # Migrate entities
        entities_data = raw_data.get("entities", {})
        entities = []
        total_observations = 0

        for name, data in entities_data.items():
            observations = data.get("observations", [])
            total_observations += len(observations)

            entities.append(Entity(
                name=name,
                type=data.get("type", "unknown"),
                observations=observations,
                created_at=data.get("created_at"),
                updated_at=data.get("created_at")  # JSON didn't have updated_at
            ))

        if entities:
            created = sqlite_backend.create_entities(entities)
            result.entities_migrated = len([c for c in created if "(updated)" not in c])
        result.observations_migrated = total_observations

        # Migrate relations
        relations_data = raw_data.get("relations", [])
        relations = []

        for rel in relations_data:
            relations.append(Relation(
                from_entity=rel["from"],
                relation_type=rel["type"],
                to_entity=rel["to"],
                created_at=rel.get("created_at")
            ))

        if relations:
            created = sqlite_backend.create_relations(relations)
            result.relations_migrated = len(created)

        # Close backends
        json_backend.close()
        sqlite_backend.close()

        # Backup JSON file
        if backup_json:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = json_path.with_suffix(f".json.backup_{timestamp}")
            shutil.copy(json_path, backup_path)
            result.json_backup_path = str(backup_path)

        result.success = True

    except Exception as e:
        result.errors.append(f"Migration failed: {str(e)}")

    return result


def validate_migration(
    json_path: Path,
    sqlite_path: Path
) -> dict:
    """Validate that migration was successful by comparing counts.

    Args:
        json_path: Path to source JSON file
        sqlite_path: Path to SQLite database

    Returns:
        Dict with validation results
    """
    json_backend = JSONBackend(json_path)
    sqlite_backend = SQLiteBackend(sqlite_path)

    json_data = json_backend.get_raw_data()
    sqlite_stats = sqlite_backend.get_stats()

    json_entities = len(json_data.get("entities", {}))
    json_relations = len(json_data.get("relations", []))
    json_observations = sum(
        len(e.get("observations", []))
        for e in json_data.get("entities", {}).values()
    )

    json_backend.close()
    sqlite_backend.close()

    return {
        "json": {
            "entities": json_entities,
            "relations": json_relations,
            "observations": json_observations
        },
        "sqlite": sqlite_stats,
        "match": {
            "entities": json_entities == sqlite_stats["entities"],
            "relations": json_relations == sqlite_stats["relations"],
            "observations": json_observations == sqlite_stats["observations"]
        },
        "valid": (
            json_entities == sqlite_stats["entities"] and
            json_relations == sqlite_stats["relations"] and
            json_observations == sqlite_stats["observations"]
        )
    }


def get_default_paths() -> tuple:
    """Get default paths for JSON and SQLite files.

    Returns:
        Tuple of (json_path, sqlite_path)
    """
    base_dir = Path.cwd()

    return (
        base_dir / "knowledge_graph.json",
        base_dir / "knowledge_graph.db"
    )
