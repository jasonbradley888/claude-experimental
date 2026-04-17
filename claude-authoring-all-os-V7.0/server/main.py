"""Entry point for the Caseware Authoring Tools Claude Desktop extension.

Reads KG_PATH from environment (set by user_config in manifest.json),
then launches the MCP server.
"""

import asyncio
import os
from pathlib import Path

from caseware_authoring_tools import server as srv


def main():
    kg_path_env = os.environ.get("KG_PATH", "").strip()
    if kg_path_env:
        srv._kg_path = Path(kg_path_env)
    else:
        # Default location
        default_dir = Path.home() / ".local" / "share" / "caseware-authoring-tools"
        default_dir.mkdir(parents=True, exist_ok=True)
        srv._kg_path = default_dir / "knowledge_graph.db"

    asyncio.run(srv._run())


if __name__ == "__main__":
    main()
