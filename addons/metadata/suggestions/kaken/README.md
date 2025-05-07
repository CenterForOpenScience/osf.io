# KAKEN Suggestion Service

## Overview

A service that indexes researcher data from KAKEN (科学研究費助成事業データベース) into Elasticsearch and provides input completion for researcher and research project information based on e-Rad IDs.

Due to the large volume of KAKEN data, the system uses ResourceSync protocol for incremental synchronization, periodically fetching only changes to reduce system load while maintaining up-to-date data.

## Architecture

```
KAKEN ResourceSync (nrid.nii.ac.jp)
    ↓
ResourceSync Client → Transformer → Elasticsearch (kaken_researchers)
                                            ↑
                                    Suggestion API (kaken:erad, kaken:kenkyusha_shimei)
```

## Key Components

### 1. Data Synchronization
- **ResourceSync Client** (`client.py`): Fetches KAKEN data
- **Transformer** (`transformer.py`): Converts data formats
- **Elasticsearch Service** (`elasticsearch.py`): Index management and search

#### Document ID Policy (ES _id)
- Source of truth: the full ResourceSync JSON URL (`_source_url`).
- ES document `_id` = SHA‑256 hex of `_source_url`.
  - Reason: avoids relying on URL path structure (e.g., trailing numeric IDs),
    guarantees stable IDs for created/updated/deleted, and works even when a
    deleted item’s JSON body is not retrievable.
- The original `accn` is kept as a field in the document for querying/display;
  it is not used as `_id`.

### 2. Celery Tasks
- **sync_kaken_data**: Periodic data synchronization (daily at 2:00 UTC)
- **cleanup_old_sync_logs**: Old log cleanup (weekly on Sunday at 3:00 UTC)

### 3. Suggestion API
- **suggest_kaken()**: Searches KAKEN data based on user input

## Configuration

```python
# Defined in addons/metadata/settings/local.py

# Elasticsearch connection settings for storing KAKEN data
# Note: In development, prefer environment variable KAKEN_ELASTIC_URI
# (e.g., http://kaken_elasticsearch:9200) via docker-compose.override.yml
KAKEN_ELASTIC_URI = os.getenv('KAKEN_ELASTIC_URI')  # None disables KAKEN features
KAKEN_ELASTIC_INDEX = 'kaken_researchers'

# Maximum number of documents to fetch from KAKEN ResourceSync URL per update
KAKEN_SYNC_MAX_DOCUMENTS_PER_EXECUTION = 10000
```

### Docker Quick Start (ES8 for KAKEN)

Add a dedicated Elasticsearch 8 service for KAKEN to `docker-compose.override.yml` and wire it to core services.

Example snippet:

```yaml
services:
  kaken_elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.14.3
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms512m -Xmx512m
    volumes:
      - kaken_elasticsearch_data_vol:/usr/share/elasticsearch/data
    restart: unless-stopped
    # platform: linux/arm64  # Uncomment on Apple Silicon if needed

  web:
    environment:
      KAKEN_ELASTIC_URI: http://kaken_elasticsearch:9200
    depends_on:
      - kaken_elasticsearch

  worker:
    environment:
      KAKEN_ELASTIC_URI: http://kaken_elasticsearch:9200
    depends_on:
      - kaken_elasticsearch

  api:
    environment:
      KAKEN_ELASTIC_URI: http://kaken_elasticsearch:9200
    depends_on:
      - kaken_elasticsearch

volumes:
  kaken_elasticsearch_data_vol:
    external: false
```

Notes:
- The KAKEN Elasticsearch is internal-only (no host port exposure) and runs single-node without security for local development.
- Set `KAKEN_ELASTIC_URI` only via environment variables (avoid hardcoding in settings).

## Usage

**Production Environment**: Automatically synchronized (daily at 2:00 UTC). No manual operations required.

**Development Environment**: Manual execution required due to Celery Beat not being defined.

### Manual Execution in Development
```bash
# Data synchronization (automatically creates index if it doesn't exist)
docker compose run --rm web python3 -m scripts.update_kaken

# Dry run (for testing)
docker compose run --rm web python3 -m scripts.update_kaken --dry-run

# Limit the number of processed docs for this run (e.g., 200)
docker compose run --rm web python3 -m scripts.update_kaken --limit 200
docker compose run --rm web python3 -m scripts.update_kaken --dry-run -l 50 -v
```

Tips:
- `--limit`/`-l` overrides `KAKEN_SYNC_MAX_DOCUMENTS_PER_EXECUTION` for the current run only.
- Add `-v` for verbose logs.

### Reset and Rebuild (one-shot)

When you want to start over cleanly (e.g., mapping/id policy changes), run:

```bash
# DANGER: clears KakenSyncLog and recreates the ES index, then runs initial sync
docker compose run --rm web python3 -m scripts.update_kaken --force-recreate --yes
```

- `--force-recreate`: Clears KakenSyncLog and deletes/recreates the index, then performs an initial sync.
- `--yes`: Skips confirmation prompt. Without it, the command asks you to confirm.
- Not compatible with `--dry-run` (the command exits with an error if combined).

## Change Lists Handling

- Action detection: strictly from `rs:md@change` (created/updated/deleted). No
  fallback heuristics are applied.
- Since filter: entries with `lastmod <= since` are excluded (boundary is
  skipped). The `since` timestamp is the last successful sync completion time.
- Deletion: derives ES `_id` from the change item’s JSON URL using the same
  SHA‑256 rule and deletes that document. No attempt is made to fetch deleted
  JSON bodies.

Notes:
- Capability list does not contain `lastmod`; resource lists include
  `rs:md@at` and per‑item `<lastmod>`. Change lists include `rs:md@from/until`
  and per‑item `<lastmod>`.

## Lastmod Semantics (Robust Incremental Sync)

- Per‑item lastmod is required.
  - Resource lists must provide a per‑item `<lastmod>`; if missing, the sync
    process fails fast with an error (no fallback heuristics).
- Per‑document watermark:
  - For every document, store the processed item `lastmod` (e.g., `_last_updated`).
  - Apply a change only when `item_lastmod > stored_lastmod` (strictly
    greater) to avoid boundary replays and out‑of‑order noise.
- Deleted documents:
  - Use a soft‑delete (store a minimal document with `deleted: true` and the
    latest processed `lastmod`) instead of hard‑deleting, so the per‑document
    watermark remains available.
  - Suggestion/search queries must exclude `deleted: true`.
- We do not rely on a global `since` or list‑level early skip; already
  processed items are naturally skipped by the per‑document comparison.

## Official Research Area Mapping (rmapV2)

To align KAKEN suggestions with the “公的資金による研究データのメタデータ登録” Research Area list, place a JSON mapping at:

`addons/metadata/suggestions/kaken/data/review_sections.json`

> The JSON mapping was created from the PDF https://researchmap.jp/outline/rmapv2/area/rmapV2_ResearchArea.pdf

Schema (array of objects):

```
[
  {
    "large_code": "A189",                // 大区分（任意）
    "large_name_ja": "…",                // 任意
    "large_name_en": "…",                // 任意
    "small_code": "09080",               // 小区分（必須：5桁）
    "small_name_ja": "科学教育関連",      // 必須
    "small_name_en": "…"                 // 任意
  }
]
```

### Suggestion Configuration
```json
{
  "key": "kaken:erad",
  "template": "<div>{{kenkyusha_shimei}}<small>{{erad}} - {{kenkyukikan_mei}} - {{kadai_mei}} (KAKEN)</small></div>",
  "autofill": {
    "number": "erad",
    "name_ja": "kenkyusha_shimei_ja_msfullname",
    "name_en": "kenkyusha_shimei_en_msfullname"
  }
}
```

See `website/project/metadata/e-rad-metadata-1.json` for details.

## Testing

```bash
docker compose run --rm web invoke test_module -n 1 -m addons/metadata/tests/test_kaken_suggestion.py
```

Included tests cover suggestion ordering/deduplication and change‑list parsing
(action from `rs:md@change`, boundary filtering by `since`).
