# Extension Audit: Caseware Authoring Tools vs MCPB Spec

> Date: 2026-03-12
> Current manifest_version: 0.2
> Latest MCPB spec versions: 0.3 / 0.4
> Extension version: 1.2.0 (manifest) / 1.1.0 (pyproject) / 1.0.0 (__init__)

---

## 1. What's Working Well

### Architecture & Design
- **Clean separation of concerns** — server.py orchestrates, cloud_proxy.py/wp_proxy.py/payload_builder.py/knowledge_graph handle domains independently
- **Dynamic tool registration** — local tools always available; Cloud and WP tools appear only when connected. Graceful degradation.
- **Bootstrap pattern** — bootstrap.py finds/installs uv, then delegates to `uv run` with inline deps. Works from Python 3.8+ system Python while the actual server requires 3.10+. Handles macOS and Windows path differences.
- **Reference prompts system** — 18 reference/workflow docs loadable via MCP prompts with section filtering. Smart name resolution (short names, prefixes, suffixes).
- **Payload builder** — Comprehensive validation (depth sequence, type-at-depth, response presence), chunking at D0 boundaries, letter two-step generation. Well tested.
- **Knowledge Graph** — Full-featured: SQLite with FTS5, entity/relation/observation model, Mermaid/GraphML/DOT export, CLI interface, migration between backends.
- **.mcpbignore** — Correctly excludes __pycache__, .pyc, .DS_Store, .venv, .db files from bundles.
- **Icon** — 2048x2048 RGBA PNG, well above the 256x256 minimum / 512x512 recommended size.
- **Test coverage** — payload_builder and wp_proxy have targeted tests covering critical validation logic.
- **Embedded instructions** — ~590 lines of always-on context for Claude Desktop covering depth system, response detection, hard-fail conditions, retry strategy, and autonomous execution rules.

### Manifest Quality
- Tools array (81 tools) is comprehensive and accurately described
- Prompts array (18 prompts) matches the _REFERENCE_PROMPTS dict in server.py
- user_config covers all required env vars with clear titles/descriptions
- Author, repository, homepage, license, keywords all populated

---

## 2. Issues Found

### CRITICAL: Manifest Version Outdated

| Field | Current | Latest Spec |
|-------|---------|-------------|
| `manifest_version` | `"0.2"` | `"0.3"` or `"0.4"` |

The spec now requires `manifest_version` of `"0.3"` or `"0.4"`. Version 0.2 is legacy. The field has also been renamed to `mcpb_version` in the current spec (though `manifest_version` may still be accepted for backward compatibility).

**Impact:** May work today but could be rejected by future Claude Desktop versions or the `mcpb validate` command.

### CRITICAL: Version Number Mismatch (3 different values)

| Location | Version |
|----------|---------|
| manifest.json | `1.2.0` |
| server/pyproject.toml | `1.1.0` |
| server/caseware_authoring_tools/__init__.py | `1.0.0` |

**Impact:** Confusing for users and developers. The manifest is what Claude Desktop shows to users. All three should match.

### HIGH: Missing `sensitive: true` on Bearer Token

Current:
```json
"bearer_token": {
  "type": "string",
  "title": "Bearer Token",
  "description": "Authentication token for the Caseware Cloud engagement.",
  "required": false
}
```

The spec supports `"sensitive": true` which tells Claude Desktop to:
- Mask the input field
- Store the value in OS keychain (macOS Keychain / Windows Credential Manager)
- Never display it in plain text

**Impact:** Bearer tokens are currently stored as plain text in extension config. This is a security gap.

### HIGH: Missing `tools_generated: true`

The server dynamically discovers and registers Cloud proxy tools and WP proxy tools at runtime (they're not known at manifest-write time). The spec provides `tools_generated: true` for exactly this case.

Current manifest lists all 81 tools statically, but the actual tool set varies based on:
- Whether Cloud is connected (adds/removes ~24 tools)
- Whether WP is connected (adds/removes 16 tools)
- What tools the remote Cloud MCP server actually exposes (could change between versions)

**Impact:** If Claude Desktop uses the manifest tool list for UI/permissions, there could be mismatches with what the server actually reports.

### HIGH: No `compatibility` Field

The spec supports:
```json
"compatibility": {
  "platforms": ["darwin", "win32"],
  "runtimes": {
    "python": ">=3.10"
  }
}
```

The extension works on macOS and Windows (bootstrap.py handles both), but this isn't declared. The Python >=3.10 requirement also isn't declared at the manifest level.

**Impact:** Users on unsupported platforms (Linux) or with incompatible Python versions get no warning at install time.

### MEDIUM: Server Type Could Use `uv` Instead of `python`

The spec (v0.4+) introduced `"type": "uv"` which:
- Uses `pyproject.toml` for dependency resolution
- Host manages Python installation automatically
- Produces smaller bundles (~100 KB vs 5-10 MB)
- No need for `server/lib/` or `server/venv/`

The current extension already uses uv via bootstrap.py — it's essentially reimplementing what the `uv` server type does natively. Switching would eliminate the custom bootstrap and simplify the architecture.

**Impact:** The bootstrap.py is 129 lines of code that the spec now handles natively. Not breaking, but unnecessary complexity.

### MEDIUM: Missing `privacy_policies` Field

The extension connects to external services (Caseware Cloud). The spec states privacy_policies URLs are "required when connecting to external services."

**Impact:** Would be required for Connectors Directory submission.

### MEDIUM: Potential Duplicate Reference File

- `Caseware_Cloud_MCP_Server_Reference.md` (67 KB)
- `caseware-cloud-mcp-full.md` (67 KB)

Both are 67 KB. The first is not referenced by any prompt in _REFERENCE_PROMPTS. If they're the same content, the duplicate adds ~67 KB to the bundle unnecessarily.

### MEDIUM: No `documentation` or `support` Fields

The spec provides these optional fields:
```json
"documentation": "https://...",
"support": "https://..."
```

The extension has `homepage` and `repository` but not dedicated docs or support URLs.

### LOW: Prompt `text` Field Contains Full Sentences

The spec shows prompt `text` as the actual prompt content (with `${arguments.arg}` placeholders). The current extension uses `text` as a description sentence like "Load the hierarchy rules reference..." rather than the prompt content itself.

This works because the server's `get_prompt()` handler loads file content dynamically, but it means the `text` field in the manifest doesn't match what the user actually sees.

### LOW: No `long_description` Field

The spec supports a `long_description` (markdown) for richer display in extension browsers/directories. Currently only `description` (one line) is provided.

### LOW: No Platform Overrides in mcp_config

The bootstrap handles platform differences in code, but the spec allows declaring platform-specific configs:
```json
"platform_overrides": {
  "win32": {"command": "python.exe", "args": [...]},
  "darwin": {"command": "python3", "args": [...]}
}
```

### LOW: Icon Could Use Modern `icons` Array

Current: `"icon": "icon.png"` (legacy field)
Spec supports: `"icons"` array with size variants and light/dark theme support.

### LOW: No `screenshots` Field

The spec supports a `screenshots` array for richer presentation in extension directories.

---

## 3. Comparison Matrix

| Spec Field | Status | Notes |
|------------|--------|-------|
| `manifest_version` / `mcpb_version` | OUTDATED | Using 0.2, spec is at 0.3/0.4 |
| `name` | OK | `caseware-authoring-tools` |
| `version` | MISMATCH | 1.2.0 / 1.1.0 / 1.0.0 across files |
| `description` | OK | Clear, concise |
| `display_name` | OK | "Caseware Authoring Tools" |
| `long_description` | MISSING | Optional but recommended |
| `author` | OK | name + url |
| `license` | OK | MIT |
| `repository` | OK | GitHub URL |
| `homepage` | OK | GitHub URL |
| `documentation` | MISSING | Optional |
| `support` | MISSING | Optional |
| `icon` | OK | Legacy format, 2048x2048 PNG |
| `icons` | MISSING | Modern array with theme support |
| `screenshots` | MISSING | Optional, for directory listing |
| `server.type` | OK | `python` |
| `server.entry_point` | OK | `server/main.py` |
| `server.mcp_config` | OK | command + args + env |
| `platform_overrides` | MISSING | Handled in bootstrap code instead |
| `tools` | OK | 81 tools declared |
| `tools_generated` | MISSING | Should be true (dynamic proxy tools) |
| `prompts` | OK | 18 prompts declared |
| `prompts_generated` | N/A | All prompts are static |
| `keywords` | OK | 9 keywords |
| `user_config` | PARTIAL | Missing `sensitive: true` on bearer_token |
| `privacy_policies` | MISSING | Required for external service connections |
| `compatibility` | MISSING | Should declare platforms + python runtime |
| `localization` | MISSING | Optional, English-only is fine |
| `_meta` | MISSING | Optional, platform-specific metadata |

---

## 4. Recommended Actions (Priority Order)

### P0 — Security
1. Add `"sensitive": true` to `bearer_token` in user_config

### P1 — Spec Compliance
2. Update `manifest_version` to `"0.3"` (or `mcpb_version` per latest naming)
3. Align version to `1.2.0` across manifest.json, pyproject.toml, and __init__.py
4. Add `"tools_generated": true` to manifest
5. Add `compatibility` object (platforms: darwin/win32, runtimes: python >=3.10)

### P2 — Best Practices
6. Add `"privacy_policies"` with Caseware privacy policy URL
7. Remove duplicate reference file (Caseware_Cloud_MCP_Server_Reference.md)
8. Add `documentation` and `support` fields

### P3 — Future Improvements
9. Evaluate switching server.type from `"python"` to `"uv"` (eliminates bootstrap.py)
10. Add `long_description` with markdown
11. Add modern `icons` array with theme variants
12. Add `screenshots` for directory submission
13. Add `platform_overrides` to mcp_config (explicit > implicit)

---

## 5. Bundle Readiness for Distribution

### For internal / direct distribution (.mcpb file sharing): READY
The extension works as-is. Users can install via double-click.

### For Connectors Directory submission: NOT YET
Missing requirements:
- [ ] Tool annotations (mandatory for directory)
- [ ] Privacy policy URLs
- [ ] Minimum 3 working examples
- [ ] Testing credentials
- [ ] Updated manifest version
- [ ] Sensitive field marking on tokens
