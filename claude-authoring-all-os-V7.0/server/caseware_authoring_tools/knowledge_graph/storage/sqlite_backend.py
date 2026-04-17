"""SQLite storage backend with FTS5 for full-text search."""

import fnmatch
import sqlite3
from pathlib import Path
from typing import List, Optional, Tuple

from ..core.models import Entity, Relation, QueryFilter, get_timestamp
from .base import StorageBackend


class SQLiteBackend(StorageBackend):
    """SQLite storage backend with FTS5 for full-text search.

    Schema:
    - entities: id, name (unique), type, created_at, updated_at
    - observations: id, entity_id (FK), content, created_at
    - relations: id, from_entity_id (FK), to_entity_id (FK), relation_type, created_at
    - entities_fts: FTS5 virtual table for entity search
    - observations_fts: FTS5 virtual table for observation search
    """

    SCHEMA = """
    -- Main entities table
    CREATE TABLE IF NOT EXISTS entities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        type TEXT NOT NULL DEFAULT 'unknown',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    -- Observations table (one-to-many with entities)
    CREATE TABLE IF NOT EXISTS observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(entity_id, content)
    );

    -- Relations table
    CREATE TABLE IF NOT EXISTS relations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
        to_entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
        relation_type TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(from_entity_id, relation_type, to_entity_id)
    );

    -- FTS5 virtual table for entity full-text search
    CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts USING fts5(
        name,
        type,
        content='entities',
        content_rowid='id'
    );

    -- FTS5 virtual table for observation full-text search
    CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts USING fts5(
        content,
        content='observations',
        content_rowid='id'
    );

    -- Triggers to keep FTS in sync with entities
    CREATE TRIGGER IF NOT EXISTS entities_ai AFTER INSERT ON entities BEGIN
        INSERT INTO entities_fts(rowid, name, type) VALUES (new.id, new.name, new.type);
    END;

    CREATE TRIGGER IF NOT EXISTS entities_ad AFTER DELETE ON entities BEGIN
        INSERT INTO entities_fts(entities_fts, rowid, name, type) VALUES('delete', old.id, old.name, old.type);
    END;

    CREATE TRIGGER IF NOT EXISTS entities_au AFTER UPDATE ON entities BEGIN
        INSERT INTO entities_fts(entities_fts, rowid, name, type) VALUES('delete', old.id, old.name, old.type);
        INSERT INTO entities_fts(rowid, name, type) VALUES (new.id, new.name, new.type);
    END;

    -- Triggers to keep FTS in sync with observations
    CREATE TRIGGER IF NOT EXISTS observations_ai AFTER INSERT ON observations BEGIN
        INSERT INTO observations_fts(rowid, content) VALUES (new.id, new.content);
    END;

    CREATE TRIGGER IF NOT EXISTS observations_ad AFTER DELETE ON observations BEGIN
        INSERT INTO observations_fts(observations_fts, rowid, content) VALUES('delete', old.id, old.content);
    END;

    -- Indexes for common queries
    CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);
    CREATE INDEX IF NOT EXISTS idx_entities_created ON entities(created_at);
    CREATE INDEX IF NOT EXISTS idx_relations_from ON relations(from_entity_id);
    CREATE INDEX IF NOT EXISTS idx_relations_to ON relations(to_entity_id);
    CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(relation_type);
    """

    def __init__(self, path: Path):
        """Initialize SQLite backend.

        Args:
            path: Path to the SQLite database file
        """
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()

    def _init_schema(self) -> None:
        """Initialize database schema."""
        self._conn.executescript(self.SCHEMA)
        self._conn.commit()

    def _get_entity_id(self, name: str) -> Optional[int]:
        """Get entity ID by name."""
        row = self._conn.execute(
            "SELECT id FROM entities WHERE name = ?", (name,)
        ).fetchone()
        return row["id"] if row else None

    def create_entities(self, entities: List[Entity]) -> List[str]:
        """Create or update multiple entities."""
        created = []
        timestamp = get_timestamp()

        for entity in entities:
            existing_id = self._get_entity_id(entity.name)

            if existing_id is None:
                # Insert new entity
                cursor = self._conn.execute(
                    """INSERT INTO entities (name, type, created_at, updated_at)
                       VALUES (?, ?, ?, ?)""",
                    (entity.name, entity.type, timestamp, timestamp)
                )
                entity_id = cursor.lastrowid
                created.append(entity.name)
            else:
                # Update existing entity type
                self._conn.execute(
                    "UPDATE entities SET type = ?, updated_at = ? WHERE id = ?",
                    (entity.type, timestamp, existing_id)
                )
                entity_id = existing_id
                created.append(f"{entity.name} (updated)")

            # Add observations
            for obs in entity.observations:
                try:
                    self._conn.execute(
                        """INSERT OR IGNORE INTO observations (entity_id, content, created_at)
                           VALUES (?, ?, ?)""",
                        (entity_id, obs, timestamp)
                    )
                except sqlite3.IntegrityError:
                    pass  # Duplicate observation

        self._conn.commit()
        return created

    def create_relations(self, relations: List[Relation]) -> List[str]:
        """Create multiple relations."""
        created = []
        timestamp = get_timestamp()

        for rel in relations:
            from_id = self._get_entity_id(rel.from_entity)
            to_id = self._get_entity_id(rel.to_entity)

            if from_id is None or to_id is None:
                # Skip relations where entities don't exist
                continue

            try:
                self._conn.execute(
                    """INSERT INTO relations (from_entity_id, to_entity_id, relation_type, created_at)
                       VALUES (?, ?, ?, ?)""",
                    (from_id, to_id, rel.relation_type, timestamp)
                )
                created.append(f"{rel.from_entity} --{rel.relation_type}--> {rel.to_entity}")
            except sqlite3.IntegrityError:
                pass  # Duplicate relation

        self._conn.commit()
        return created

    def add_observations(self, entity_name: str, observations: List[str]) -> List[str]:
        """Add observations to an entity."""
        added = []
        timestamp = get_timestamp()

        entity_id = self._get_entity_id(entity_name)
        if entity_id is None:
            # Auto-create entity
            cursor = self._conn.execute(
                """INSERT INTO entities (name, type, created_at, updated_at)
                   VALUES (?, 'unknown', ?, ?)""",
                (entity_name, timestamp, timestamp)
            )
            entity_id = cursor.lastrowid

        for obs in observations:
            try:
                self._conn.execute(
                    """INSERT INTO observations (entity_id, content, created_at)
                       VALUES (?, ?, ?)""",
                    (entity_id, obs, timestamp)
                )
                added.append(obs)
            except sqlite3.IntegrityError:
                pass  # Duplicate observation

        if added:
            self._conn.execute(
                "UPDATE entities SET updated_at = ? WHERE id = ?",
                (timestamp, entity_id)
            )

        self._conn.commit()
        return added

    def query(self, filter: QueryFilter) -> List[Entity]:
        """Query entities matching filter criteria."""
        # Start with base query
        query = """
            SELECT e.id, e.name, e.type, e.created_at, e.updated_at
            FROM entities e
            WHERE 1=1
        """
        params = []

        # Filter by type
        if filter.entity_type:
            query += " AND e.type = ?"
            params.append(filter.entity_type)

        # Filter by created_after
        if filter.created_after:
            query += " AND e.created_at >= ?"
            params.append(filter.created_after)

        # Filter by created_before
        if filter.created_before:
            query += " AND e.created_at <= ?"
            params.append(filter.created_before)

        # Filter by related_to
        if filter.related_to:
            related_id = self._get_entity_id(filter.related_to)
            if related_id:
                query += """
                    AND e.id IN (
                        SELECT to_entity_id FROM relations WHERE from_entity_id = ?
                        UNION
                        SELECT from_entity_id FROM relations WHERE to_entity_id = ?
                    )
                """
                params.extend([related_id, related_id])
            else:
                return []  # Related entity doesn't exist

        rows = self._conn.execute(query, params).fetchall()
        results = []

        for row in rows:
            name = row["name"]

            # Filter by glob pattern (done in Python since SQLite doesn't support glob well)
            if filter.pattern and not fnmatch.fnmatch(name, filter.pattern):
                continue

            # Get observations
            obs_rows = self._conn.execute(
                "SELECT content FROM observations WHERE entity_id = ?",
                (row["id"],)
            ).fetchall()
            observations = [r["content"] for r in obs_rows]

            results.append(Entity(
                name=name,
                type=row["type"],
                observations=observations,
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            ))

        return results

    def search(self, query: str, fields: Optional[List[str]] = None) -> List[Entity]:
        """Full-text search across entities using FTS5."""
        if fields is None:
            fields = ["name", "type", "observations"]

        entity_ids = set()

        # Search entities FTS
        if "name" in fields or "type" in fields:
            fts_fields = []
            if "name" in fields:
                fts_fields.append("name")
            if "type" in fields:
                fts_fields.append("type")

            if fts_fields:
                fts_query = " OR ".join(f"{f}:{query}" for f in fts_fields)
                try:
                    rows = self._conn.execute(
                        "SELECT rowid FROM entities_fts WHERE entities_fts MATCH ?",
                        (fts_query,)
                    ).fetchall()
                    entity_ids.update(r["rowid"] for r in rows)
                except sqlite3.OperationalError:
                    # Fallback to LIKE query if FTS fails
                    for field in fts_fields:
                        rows = self._conn.execute(
                            f"SELECT id FROM entities WHERE {field} LIKE ?",
                            (f"%{query}%",)
                        ).fetchall()
                        entity_ids.update(r["id"] for r in rows)

        # Search observations FTS
        if "observations" in fields:
            try:
                rows = self._conn.execute(
                    """SELECT DISTINCT entity_id FROM observations
                       WHERE id IN (SELECT rowid FROM observations_fts WHERE observations_fts MATCH ?)""",
                    (query,)
                ).fetchall()
                entity_ids.update(r["entity_id"] for r in rows)
            except sqlite3.OperationalError:
                # Fallback to LIKE query
                rows = self._conn.execute(
                    "SELECT DISTINCT entity_id FROM observations WHERE content LIKE ?",
                    (f"%{query}%",)
                ).fetchall()
                entity_ids.update(r["entity_id"] for r in rows)

        if not entity_ids:
            return []

        # Fetch full entities
        placeholders = ",".join("?" for _ in entity_ids)
        rows = self._conn.execute(
            f"SELECT id, name, type, created_at, updated_at FROM entities WHERE id IN ({placeholders})",
            list(entity_ids)
        ).fetchall()

        results = []
        for row in rows:
            obs_rows = self._conn.execute(
                "SELECT content FROM observations WHERE entity_id = ?",
                (row["id"],)
            ).fetchall()
            observations = [r["content"] for r in obs_rows]

            results.append(Entity(
                name=row["name"],
                type=row["type"],
                observations=observations,
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            ))

        return results

    def get(self, entity_name: str) -> Optional[Entity]:
        """Get a single entity by name."""
        row = self._conn.execute(
            "SELECT id, name, type, created_at, updated_at FROM entities WHERE name = ?",
            (entity_name,)
        ).fetchone()

        if not row:
            return None

        obs_rows = self._conn.execute(
            "SELECT content FROM observations WHERE entity_id = ?",
            (row["id"],)
        ).fetchall()
        observations = [r["content"] for r in obs_rows]

        return Entity(
            name=row["name"],
            type=row["type"],
            observations=observations,
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    def get_with_relations(self, entity_name: str) -> Optional[dict]:
        """Get entity with its relations."""
        entity = self.get(entity_name)
        if not entity:
            return None

        entity_id = self._get_entity_id(entity_name)

        # Get outgoing relations
        outgoing_rows = self._conn.execute(
            """SELECT e.name as to_name, r.relation_type, r.created_at
               FROM relations r
               JOIN entities e ON r.to_entity_id = e.id
               WHERE r.from_entity_id = ?""",
            (entity_id,)
        ).fetchall()

        # Get incoming relations
        incoming_rows = self._conn.execute(
            """SELECT e.name as from_name, r.relation_type, r.created_at
               FROM relations r
               JOIN entities e ON r.from_entity_id = e.id
               WHERE r.to_entity_id = ?""",
            (entity_id,)
        ).fetchall()

        return {
            "name": entity.name,
            "type": entity.type,
            "observations": entity.observations,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "outgoing_relations": [
                {"from": entity_name, "type": r["relation_type"], "to": r["to_name"], "created_at": r["created_at"]}
                for r in outgoing_rows
            ],
            "incoming_relations": [
                {"from": r["from_name"], "type": r["relation_type"], "to": entity_name, "created_at": r["created_at"]}
                for r in incoming_rows
            ]
        }

    def delete(self, entity_name: str) -> bool:
        """Delete an entity and its relations."""
        entity_id = self._get_entity_id(entity_name)
        if entity_id is None:
            return False

        # Relations and observations are deleted via CASCADE
        self._conn.execute("DELETE FROM entities WHERE id = ?", (entity_id,))
        self._conn.commit()
        return True

    def list_entities(self) -> List[dict]:
        """List all entities with summary info."""
        rows = self._conn.execute(
            """SELECT e.name, e.type, e.created_at,
                      (SELECT COUNT(*) FROM observations WHERE entity_id = e.id) as obs_count
               FROM entities e
               ORDER BY e.created_at DESC"""
        ).fetchall()

        return [
            {
                "name": r["name"],
                "type": r["type"],
                "observations_count": r["obs_count"],
                "created_at": r["created_at"]
            }
            for r in rows
        ]

    def get_graph_data(self) -> Tuple[List[Entity], List[Relation]]:
        """Get all entities and relations."""
        # Get all entities
        entity_rows = self._conn.execute(
            "SELECT id, name, type, created_at, updated_at FROM entities"
        ).fetchall()

        entities = []
        for row in entity_rows:
            obs_rows = self._conn.execute(
                "SELECT content FROM observations WHERE entity_id = ?",
                (row["id"],)
            ).fetchall()
            observations = [r["content"] for r in obs_rows]

            entities.append(Entity(
                name=row["name"],
                type=row["type"],
                observations=observations,
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            ))

        # Get all relations
        rel_rows = self._conn.execute(
            """SELECT e1.name as from_name, r.relation_type, e2.name as to_name, r.created_at
               FROM relations r
               JOIN entities e1 ON r.from_entity_id = e1.id
               JOIN entities e2 ON r.to_entity_id = e2.id"""
        ).fetchall()

        relations = [
            Relation(
                from_entity=r["from_name"],
                relation_type=r["relation_type"],
                to_entity=r["to_name"],
                created_at=r["created_at"]
            )
            for r in rel_rows
        ]

        return entities, relations

    def get_relations(self, entity_name: Optional[str] = None) -> List[Relation]:
        """Get relations, optionally filtered by entity."""
        if entity_name is None:
            rows = self._conn.execute(
                """SELECT e1.name as from_name, r.relation_type, e2.name as to_name, r.created_at
                   FROM relations r
                   JOIN entities e1 ON r.from_entity_id = e1.id
                   JOIN entities e2 ON r.to_entity_id = e2.id"""
            ).fetchall()
        else:
            entity_id = self._get_entity_id(entity_name)
            if entity_id is None:
                return []

            rows = self._conn.execute(
                """SELECT e1.name as from_name, r.relation_type, e2.name as to_name, r.created_at
                   FROM relations r
                   JOIN entities e1 ON r.from_entity_id = e1.id
                   JOIN entities e2 ON r.to_entity_id = e2.id
                   WHERE r.from_entity_id = ? OR r.to_entity_id = ?""",
                (entity_id, entity_id)
            ).fetchall()

        return [
            Relation(
                from_entity=r["from_name"],
                relation_type=r["relation_type"],
                to_entity=r["to_name"],
                created_at=r["created_at"]
            )
            for r in rows
        ]

    def clear(self) -> bool:
        """Clear all data."""
        self._conn.execute("DELETE FROM relations")
        self._conn.execute("DELETE FROM observations")
        self._conn.execute("DELETE FROM entities")
        self._conn.commit()
        return True

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def get_stats(self) -> dict:
        """Get database statistics."""
        entity_count = self._conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        relation_count = self._conn.execute("SELECT COUNT(*) FROM relations").fetchone()[0]
        observation_count = self._conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]

        return {
            "entities": entity_count,
            "relations": relation_count,
            "observations": observation_count
        }
