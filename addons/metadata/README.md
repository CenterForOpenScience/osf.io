# RDM Metadata Addon

## Feature

The RDM Metadata Addon provides a way to edit metadata for projects or files. Users can enable the addon for their project and edit metadata for the project or files.

The detailed features of the RDM Metadata Addon are as follows:

- Edit metadata for projects or files
- View metadata for projects or files
- Export metadata for projects to various formats/destinations
- Export and import projects in RO-Crate format
- Import datasets from external sources

## Enabling the feature

### Export and import projects in RO-Crate format

To enable the feature, you should add the following settings to the configuration file `addons/metadata/settings/local.py`:

```python
USE_EXPORTING = True
```

The "Export" tab is displayed in a project dashboard if `USE_EXPORTING` is true and users can export the project in RO-Crate format.

### Import datasets from external sources

To enable the feature, you should add the following settings to the configuration file `addons/metadata/settings/local.py`:

```python
USE_DATASET_IMPORTING = True
```

The "Import Dataset" button is displayed in a toolbar of a file browser if `USE_DATASET_IMPORTING` is true and users can import datasets from external sources.

## Suggestion Policies (ERAD/KAKEN)

This addon provides researcher/project suggestions sourced from ERAD and KAKEN. Ordering and deduplication follow simple, explicit policies so results are predictable and easy to reason about.

### Sorting

- Owner: current user first, then other contributors in `node.contributors` order.
- Year: within each owner, sort by fiscal year (`nendo`) descending.
- Key priority: then apply `key_list` priority (place `contributor:*` earlier if you want it prioritized).
- Researcher/Project ordering flow (e.g. for KAKEN suggestions):
  1. Seed with the current user's e-Rad researcher number, query Elasticsearch for matching projects, sort the projects by fiscal year (descending), and enumerate collaborators (`work:project.member`) exactly as stored. For collaborators with an e-Rad number but no English name, fetch the English name from Elasticsearch keyed by that number.
  2. For each remaining project member, follow their contributor order, query Elasticsearch for their projects, and reuse the collaborator enumeration from step 1. Ensure the project member themselves appears immediately after the current user in the combined results.
  3. Deduplicate the consolidated list. A researcher entry is considered a duplicate when the e-Rad number, Japanese/English names, and Japanese/English affiliation names all match; keep the first occurrence. A project entry is considered a duplicate if the project number matches; keep the first occurrence.

### Deduplication

Unified approach for all modes: first apply the sorting above (owner → year desc → key priority), then keep the first occurrence per identity.

- person identity: [ERAD researcher number (`erad` or `kenkyusha_no`), normalized name (MSFullName), normalized institution name ja (`kenkyukikan_mei_ja`)]
- project identity: `kadai_id` (or if absent, `japan_grant_number`)

### Policy Selection (by full key)

Policy is inferred by the full key `<prefix>:<field>` with explicit mappings to avoid ambiguities:

- person keys:
  - `contributor:erad`, `contributor:name`, `contributor:affiliated-institution-name`
  - `erad:kenkyusha_no`, `erad:kenkyusha_shimei`
  - `kaken:erad`, `kaken:kenkyusha_shimei` (and `_ja`, `_en` variants)
- project keys:
  - ERAD: `erad:kadai_id`, `erad:japan_grant_number`, `erad:nendo`, `erad:kadai_mei`, `erad:program_name_*`, `erad:haibunkikan_*`, `erad:bunya_*`
  - KAKEN: `kaken:kadai_id`, `kaken:japan_grant_number`, `kaken:nendo`, `kaken:kadai_mei`, `kaken:program_name_*`, `kaken:haibunkikan_*`, `kaken:bunya_*`

There is no prefix‑based fallback for single‑key requests; classification is always determined by the field suffix.

Mixed requests (person + project keys together):

- No cross‑key merge/dedup is applied. Suggestions are returned in the concatenated order (i.e., `key_list` order, with each key’s internal order preserved).

### Endpoint Behavior

- `suggestion_erad` (keys starting with `erad:`): applies person mode.
- `suggest_kaken` (keys starting with `kaken:`): applies project mode.
- `metadata_file_metadata_suggestions`:
  - If all keys are person or all project: sort (owner → year desc → key priority) and keep first occurrence per identity.
  - If person and project keys are mixed: no cross‑key merge/dedup; suggestions are concatenated in request `key_list` order (each key’s internal order preserved).
- `metadata_get_erad_candidates`: orders by owner → year desc; deduplicates by project identity keeping the first appearance.

Notes:

- Sorting is a stable sort; when tie‑breaking cannot decide, original order is preserved.
- Identifiers used for deduplication are chosen conservatively to avoid false merges (e.g., prefer explicit IDs over normalized names).
