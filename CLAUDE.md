# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Development Commands

```bash
# Install for development
pip install -e ".[tests]"

# Run unit tests
pytest -v

# Run a single test file
pytest -v tests/unit/test_file.py

# Run a single test
pytest -v tests/unit/test_file.py::test_name

# Run integration tests (requires DD_SOURCE_* and DD_DESTINATION_* env vars)
pytest -v -m "integration"

# Lint with ruff
tox -e ruff

# Format with black
tox -e black

# Run all tox environments
tox
```

## Code Style

- Line length: 120 characters
- Formatter: black
- Linter: ruff

## Architecture

### CLI Commands

Entry point is `datadog_sync/cli.py`. Commands are defined in `datadog_sync/commands/`:
- `import` - Reads resources from source org, stores in `resources/source/`
- `sync` - Creates/updates resources in destination org from local files
- `diffs` - Shows what would change without applying
- `migrate` - Runs import then sync
- `reset` - Deletes resources at destination (with backup)

### Resource Model System

Resources are defined in `datadog_sync/model/`. Each resource class:
1. Inherits from `BaseResource` (`datadog_sync/utils/base_resource.py`)
2. Sets `resource_type` (string identifier) and `resource_config` (ResourceConfig dataclass)
3. Implements abstract methods: `get_resources`, `import_resource`, `create_resource`, `update_resource`, `delete_resource`, `pre_resource_action_hook`, `pre_apply_hook`

Resources are auto-discovered at runtime - any class inheriting `BaseResource` is registered.

### ResourceConfig

Key fields in `ResourceConfig`:
- `base_path`: API endpoint path (e.g., `/api/v1/monitor`)
- `resource_connections`: Dict mapping dependent resource types to attribute paths for ID remapping
- `excluded_attributes`: Fields to ignore during sync/diff (dot notation, converted to deepdiff paths)
- `concurrent`: Whether resource can be synced in parallel (default True)
- `tagging_config`: Optional TaggingConfig for adding default tags

### State Management

State is stored in `resources/` directory:
- `resources/source/*.json` - Source org resources keyed by ID
- `resources/destination/*.json` - Destination org resources with ID mappings

The `connect_resources` method in BaseResource handles remapping IDs between orgs using `resource_connections`.

### HTTP Client

`datadog_sync/utils/custom_client.py` provides `CustomClient` for async HTTP requests with:
- Pagination support via `PaginationConfig`
- Retry logic
- Rate limiting
