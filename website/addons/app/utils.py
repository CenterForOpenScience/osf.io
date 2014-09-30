# -*- coding: utf-8 -*-
"""Utility functions for the Application add-on.
"""
from __future__ import unicode_literals

from framework.guid.model import Metadata

from website.search import search


def create_orphaned_metadata(node_addon, report):
    metastore = Metadata(app=node_addon)
    metastore.update(report)
    metastore.system_data['is_orphan'] = True
    metastore.system_data['guid'] = metastore._id
    metastore.save()

    search.update_metadata(metastore)

    return metastore
