from comments import *
from common import *
from groups import *
from topics import *
from users import *

import ipdb

def sync_project(project_node):
    from website.addons.wiki.model import NodeWikiPage
    from website.files.models import StoredFileNode
    from modularodm import Q

    sync_group(project_node)

    if project_node.discourse_topic_id:
        update_topic_title(project_node)
        update_topic_content(project_node)

def delete_project(project_node):
    delete_group(project_node)
