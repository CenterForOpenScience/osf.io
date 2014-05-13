# -*- coding: utf-8 -*-
"""Various node-related utilities."""
from website.project.views import node
from website.project.views import file as file_views


# Alias the project serializer
serialize_node = node._view_project

# File rendering utils
get_cache_content = file_views.get_cache_content
get_cache_path = file_views.get_cache_path
prepare_file = file_views.prepare_file
