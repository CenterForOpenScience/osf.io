# -*- coding: utf-8 -*-
import uuid

from django.apps import apps
from django.core.exceptions import ValidationError

from framework.auth.core import Auth
from website.exceptions import NodeStateError
from osf.utils.sanitize import strip_html

# TODO: This should be a class method of Node
def new_node(category, title, user, description='', parent=None):
    """Create a new project or component.

    :param str category: Node category
    :param str title: Node title
    :param User user: User object
    :param str description: Node description
    :param Node project: Optional parent object
    :return Node: Created node

    """
    # We use apps.get_model rather than import .model.Node
    # because we want the concrete Node class, not AbstractNode
    Node = apps.get_model('osf.Node')
    category = category
    title = strip_html(title.strip())
    if description:
        description = strip_html(description.strip())

    node = Node(
        title=title,
        category=category,
        creator=user,
        description=description,
        parent=parent
    )

    node.save()

    return node


def new_bookmark_collection(user):
    """Create a new bookmark collection project.

    :param User user: User object
    :return Node: Created node

    """
    Collection = apps.get_model('osf.Collection')
    existing_bookmark_collections = Collection.objects.filter(
        is_bookmark_collection=True,
        creator=user,
        deleted__isnull=True
    ).exists()

    if existing_bookmark_collections:
        raise NodeStateError('Users may only have one bookmark collection')

    collection = Collection(
        title='Bookmarks',
        creator=user,
        is_bookmark_collection=True
    )
    collection.save()
    return collection


def new_private_link(name, user, nodes, anonymous):
    """Create a new private link.

    :param str name: private link name
    :param User user: User object
    :param list Node node: a list of node object
    :param bool anonymous: make link anonymous or not
    :return PrivateLink: Created private link

    """
    PrivateLink = apps.get_model('osf.PrivateLink')
    NodeLog = apps.get_model('osf.NodeLog')

    key = str(uuid.uuid4()).replace('-', '')
    if name:
        name = strip_html(name)
        if name is None or not name.strip():
            raise ValidationError('Invalid link name.')
    else:
        name = 'Shared project link'

    private_link = PrivateLink(
        key=key,
        name=name,
        creator=user,
        anonymous=anonymous
    )

    private_link.save()

    private_link.nodes.add(*nodes)

    auth = Auth(user)
    for node in nodes:
        log_dict = {
            'project': node.parent_id,
            'node': node._id,
            'user': user._id,
            'anonymous_link': anonymous,
        }

        node.add_log(
            NodeLog.VIEW_ONLY_LINK_ADDED,
            log_dict,
            auth=auth
        )

    private_link.save()

    return private_link
