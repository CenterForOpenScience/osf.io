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
