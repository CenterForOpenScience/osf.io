from comments import *
from common import *
from groups import *
from topics import *
from users import *

def sync_project(project_node):
    if in_migration:
        return

    sync_group(project_node)

    if project_node.discourse_topic_id:
        sync_topic(project_node)
    else:
        create_topic(project_node)

def delete_project(project_node):
    delete_group(project_node)
