# MCPB Manifest.json Specification

> Source: https://github.com/anthropics/mcpb/blob/main/MANIFEST.md
> Fetched: 2026-03-12

---

## Top-Level Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `manifest_version` | string | `"0.3"` or `"0.4"` — specification version |
| `name` | string | Machine-readable identifier for CLI/APIs |
| `version` | string | Semantic versioning format |
| `description` | string | Brief overview (localizable) |
| `author` | object | Required: `name`; optional: `email`, `url` |
| `server` | object | Configuration object defining execution |

## Top-Level Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `display_name` | string | UI-friendly name (localizable) |
| `long_description` | string | Extended markdown details (localizable) |
| `repository` | object | Git source with `type` and `url` |
| `homepage` | string | Extension URL |
| `documentation` | string | Docs URL |
| `support` | string | Issues/support URL |
| `icon` | string | Single PNG path or HTTPS URL |
| `icons` | array | Variants with `src`, `size` (WIDTHxHEIGHT), optional `theme` |
| `screenshots` | array | Image paths |
| `tools` | array | Describing provided tools (localizable) |
| `tools_generated` | boolean | Server generates tools beyond manifest list |
| `prompts` | array | Describing provided prompts (localizable) |
| `prompts_generated` | boolean | Server generates prompts beyond manifest list |
| `keywords` | array | Search terms (localizable) |
| `license` | string | Identifier like MIT |
| `privacy_policies` | array | URLs required when connecting to external services |
| `compatibility` | object | Version/platform constraints |
| `user_config` | object | User-facing configuration options |
| `localization` | object | Resource path and default locale |
| `_meta` | object | Platform-specific metadata (reverse-DNS keyed) |

---

## Server Configuration (`server` object)

### Server Types

| Type | Description |
|------|-------------|
| `"node"` | Node.js with bundled dependencies |
| `"python"` | Python with bundled dependencies |
| `"binary"` | Compiled executable |
| `"uv"` | Python via UV runtime (experimental, v0.4+) |

### Required Server Fields

- **type**: One of the four types above
- **entry_point**: Path to main file

### MCP Configuration (`mcp_config`)

```json
{
  "command": "string",
  "args": ["string array"],
  "env": {"key": "value"},
  "platform_overrides": {
    "win32": {"command": "...", "args": [], "env": {}},
    "darwin": {"command": "...", "args": [], "env": {}},
    "linux": {"command": "...", "args": [], "env": {}}
  }
}
```

### Variable Substitution

| Variable | Description |
|----------|-------------|
| `${__dirname}` | Extension directory absolute path |
| `${HOME}` | User home directory |
| `${DESKTOP}` | Desktop directory |
| `${DOCUMENTS}` | Documents directory |
| `${DOWNLOADS}` | Downloads directory |
| `${pathSeparator}` or `${/}` | Platform path separator |
| `${user_config.KEY}` | User-provided configuration value |

### Platform Override Example

```json
"platform_overrides": {
  "win32": {
    "command": "server/my-server.exe",
    "args": ["--config", "server/config-windows.json"]
  }
}
```

### UV Runtime (Experimental, v0.4+)

- Must include `pyproject.toml` with dependencies
- Must NOT include `server/lib/` or `server/venv/`
- `mcp_config` is optional
- Small bundle (~100 KB vs 5-10 MB)

---

## User Configuration (`user_config`)

| Property | Values | Purpose |
|----------|--------|---------|
| `type` | `"string"`, `"number"`, `"boolean"`, `"directory"`, `"file"` | Data type |
| `title` | string | UI display label |
| `description` | string | Help text |
| `required` | boolean | Must provide value (default: false) |
| `default` | varies | Initial value; supports `${HOME}`, `${DESKTOP}`, `${DOCUMENTS}` |
| `multiple` | boolean | Multiple selections for directory/file (default: false) |
| `sensitive` | boolean | Mask input, store securely for strings (default: false) |
| `min` | number | Minimum for number type |
| `max` | number | Maximum for number type |

Array expansion: When `multiple: true` configuration appears in `args`, each value becomes a separate argument.

---

## Tools and Prompts

### Tools Array Structure

```json
"tools": [
  {
    "name": "tool_identifier",
    "description": "What it does"
  }
]
```

### Prompts Array Structure

```json
"prompts": [
  {
    "name": "prompt_id",
    "description": "Purpose",
    "arguments": ["arg1", "arg2"],
    "text": "Text using ${arguments.arg1} placeholders"
  }
]
```

### Dynamic Capability Flags

- **tools_generated**: `true` = server generates tools beyond manifest list
- **prompts_generated**: `true` = server generates prompts beyond manifest list

---

## Compatibility Object

```json
{
  "compatibility": {
    "claude_desktop": ">=1.0.0",
    "platforms": ["darwin", "win32", "linux"],
    "runtimes": {
      "python": ">=3.8",
      "node": ">=16.0.0"
    }
  }
}
```

- Client version constraints use semver syntax
- **platforms**: `darwin` (macOS), `win32` (Windows), `linux`
- **runtimes**: Only specify for runtime types used

---

## Localization

```json
{
  "localization": {
    "resources": "mcpb-resources/${locale}.json",
    "default_locale": "en-US"
  }
}
```

- `resources` must contain `${locale}` placeholder
- `default_locale` must be BCP 47 identifier
- Clients apply fallbacks (e.g., `es-UY` -> `es-MX` -> `es-ES` -> manifest)

---

## Icons

Legacy:
```json
"icon": "icon.png"
```

Modern (with theme variants):
```json
"icons": [
  {"src": "assets/icons/icon-16-light.png", "size": "16x16", "theme": "light"},
  {"src": "assets/icons/icon-16-dark.png", "size": "16x16", "theme": "dark"}
]
```

---

## Platform-Specific Metadata (`_meta`)

```json
"_meta": {
  "com.microsoft.windows": {
    "package_family_name": "...",
    "static_responses": {
      "initialize": {},
      "tools/list": {}
    }
  }
}
```

Uses reverse-DNS namespacing for platform identification.

---

## MCPB CLI Reference

### Installation

```bash
npm install -g @anthropic-ai/mcpb
```

### Commands

| Command | Purpose |
|---------|---------|
| `mcpb init` | Interactive manifest.json creation |
| `mcpb validate` | Check manifest against schema |
| `mcpb pack` | Bundle directory into .mcpb file |
| `mcpb sign` | Apply digital signature (--cert, --key, --intermediate, --self-signed) |
| `mcpb verify` | Confirm signature validity |
| `mcpb info` | Display extension file details |
| `mcpb unsign` | Remove signature from file |

### Pack Behavior

- Auto-validates manifest
- Excludes development files (.DS_Store, Thumbs.db, .git/, *.log, node_modules cache, lock files)
- Applies maximum compression
- Custom exclusions via `.mcpbignore` (supports exact matches, globs, directory paths, comments)

### Signature Format

- X.509 certificate (PEM) with code signing extended key usage
- PKCS#7 DER-encoded, appended with `MCPB_SIG_V1`/`MCPB_SIG_END` markers
- Preserves ZIP compatibility

---

## Bundle Structure Examples

### Node.js
```
bundle.mcpb (ZIP)
  manifest.json
  server/index.js
  node_modules/
  package.json
  icon.png
```

### Python
```
bundle.mcpb (ZIP)
  manifest.json
  server/main.py
  lib/
  requirements.txt
  icon.png
```

### UV (Experimental)
```
bundle.mcpb (ZIP)
  manifest.json
  server/main.py
  pyproject.toml
  icon.png
```

### Binary
```
bundle.mcpb (ZIP)
  manifest.json
  server/my-server (unix)
  server/my-server.exe (windows)
  icon.png
```
