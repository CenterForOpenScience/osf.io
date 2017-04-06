# -*- coding: utf-8 -*-
import uuid

from django.apps import apps

from .model import PrivateLink
from framework.mongo.utils import from_mongo
from modularodm import Q
from modularodm.exceptions import ValidationValueError
from website.exceptions import NodeStateError
from website.util.sanitize import strip_html

def show_diff(seqm):
    """Unify operations between two compared strings
seqm is a difflib.SequenceMatcher instance whose a & b are strings"""
    output = []
    insert_el = '<span style="background:#4AA02C; font-size:1.5em; ">'
    ins_el_close = '</span>'
    del_el = '<span style="background:#D16587; font-size:1.5em;">'
    del_el_close = '</span>'
    for opcode, a0, a1, b0, b1 in seqm.get_opcodes():
        content_a = strip_html(seqm.a[a0:a1])
        content_b = strip_html(seqm.b[b0:b1])
        if opcode == 'equal':
            output.append(content_a)
        elif opcode == 'insert':
            output.append(insert_el + content_b + ins_el_close)
        elif opcode == 'delete':
            output.append(del_el + content_a + del_el_close)
        elif opcode == 'replace':
            output.append(del_el + content_a + del_el_close + insert_el + content_b + ins_el_close)
        else:
            raise RuntimeError('unexpected opcode')
    return ''.join(output)

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
    existing_bookmark_collection = Collection.find(
        Q('is_bookmark_collection', 'eq', True) &
        Q('creator', 'eq', user) &
        Q('is_deleted', 'eq', False)
    )

    if existing_bookmark_collection.count() > 0:
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
    key = str(uuid.uuid4()).replace('-', '')
    if name:
        name = strip_html(name)
        if name is None or not name.strip():
            raise ValidationValueError('Invalid link name.')
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

    private_link.save()

    return private_link


template_name_replacements = {
    ('.txt', ''),
    ('_', ' '),
}


def clean_template_name(template_name):
    template_name = from_mongo(template_name)
    for replacement in template_name_replacements:
        template_name = template_name.replace(*replacement)
    return template_name
