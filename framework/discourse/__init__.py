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
    update_topic_title(project_node)
    update_topic_content(project_node)
    update_topic_privacy(project_node)

    for key, wiki_id in project_node.wiki_pages_current.items():
        wiki = NodeWikiPage.load(wiki_id)
        update_topic_privacy(wiki)

    file_nodes = StoredFileNode.find(Q('node', 'eq', project_node) &
                                     Q('discourse_topic_id', 'ne', None) &
                                     Q('discourse_topic_public', 'ne', project_node.is_public))

    for file_node in file_nodes:
        update_topic_privacy(file_node)

def delete_project(project_node):
    delete_group(project_node)
