"""Versioned, server-owned defaults; each run stores its resolved configuration."""
from copy import deepcopy

PRESETS = {
    'load': {'label': 'Custom load test', 'version': 1, 'defaults': {}},
    'retry': {'label': 'Retry and recovery', 'version': 2,
              'defaults': {'queue': 'celery', 'tasks_per_scenario': 1, 'transient_failures': 2, 'retry_delay': 2, 'max_retries': 3, 'deadline_seconds': 120}},
    'workflow': {'label': 'Workflow correctness', 'version': 2,
                 'defaults': {'queue': 'celery', 'workflow_count': 1, 'chain_length': 2, 'group_size': 3, 'chord_size': 3, 'deadline_seconds': 120}},
}


def resolve(preset, overrides):
    definition = PRESETS[preset]
    return {**deepcopy(definition['defaults']), **overrides,
            'suite_type': preset, 'preset_version': definition['version']}
