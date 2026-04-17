#!/usr/bin/env bash
# Build the Caseware Authoring Tools Claude Desktop extension (.mcpb)
#
# Usage:
#   ./build-extension.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
EXT_DIR="$REPO_ROOT/claude-authoring-all-os-V7.0"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check mcpb is installed
if ! command -v mcpb &>/dev/null; then
    echo -e "${YELLOW}mcpb CLI not found. Install with: npm install -g @anthropic-ai/mcpb${NC}"
    exit 1
fi

echo -e "${GREEN}Validating manifest...${NC}"
mcpb validate "$EXT_DIR/manifest.json"

echo -e "${GREEN}Packing extension...${NC}"
mcpb pack "$EXT_DIR/"

echo -e "${GREEN}Extension packed successfully!${NC}"
echo -e "Look for the .mcpb file in the current directory."
