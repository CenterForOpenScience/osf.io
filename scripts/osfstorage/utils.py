#!/usr/bin/env python
# encoding: utf-8


def ensure_osf_files(settings):
    """Ensure `osffiles` is enabled for access to legacy models.
    """
    settings.COPY_GIT_REPOS = True
    if 'osffiles' not in settings.ADDONS_REQUESTED:
        settings.ADDONS_REQUESTED.append('osffiles')
