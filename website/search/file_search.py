import base64

from website.project.model import Node
from website.search import file_util
from elastic_search import es, INDEX, get_doctype_from_node


def build_file_body(file_node, parent=None, content=None):
    parent = parent or file_node.parent
    file_doc = {
        'name': file_node.name,
        'path': file_node._id,
        'parent': parent._id,
        'attachment': base64.encodestring(content),
        'category': 'file'
    }
    return file_doc


@file_util.require_file_indexing
def retrieve(id, parent_id, doc_type, index=None):
    index = index or INDEX
    doc = es.get(
        index=index,
        doc_type=doc_type,
        id=id,
        parent=parent_id,
        ignore=[404],
    )
    if not doc['found']:
        return False
    return doc['_source']


@file_util.require_file_indexing
def index_doc(id, parent_id, doc_type, body, index=None):
    index = index or INDEX
    es.index(
        index=index,
        doc_type=doc_type,
        id=id,
        parent=parent_id,
        body=body,
    )


@file_util.require_file_indexing
def delete_doc(id, parent_id, doc_type, index=None):
    index = index or INDEX
    es.delete(
        index=index,
        doc_type=doc_type,
        parent=parent_id,
        id=id,
        refresh=True,
        ignore=[404],
    )


@file_util.require_file_indexing
def update_to(file_node, node, content=None, index=None):
    """ Insert a filenode into search index as child of node.

    :param file_node: filenode to be inserted.
    :param node: node to be made parent of filenode.
    :param content: text content of filenode.
    """

    index = index or INDEX

    if node.is_public:
        doc_type = '{}_file'.format(get_doctype_from_node(node))
        file_body = build_file_body(file_node, parent=node, content=content)
        print(file_body)
        index_doc(
            id=file_node._id,
            parent_id=node._id,
            doc_type=doc_type,
            body=file_body,
            index=index,
        )


@file_util.require_file_indexing
def delete_from(file_node, node_id, index=None):
    """ Delete a filenode from the search index.

    :param file_node: filenode to be deleted.
    :param node_id: guid of filenode's parent.
    """

    index = index or INDEX
    node = Node.load(node_id)
    doc_type = '{}_file'.format(get_doctype_from_node(node))
    es.delete(
        index=index,
        doc_type=doc_type,
        id=file_node._id,
        parent=node._id,
        ignore=[404],
    )


@file_util.require_file_indexing
def copy_file(old_file_node, new_file_node_id, old_parent_id, new_parent_id, content=None, index=None):
    index = index or INDEX
    old_parent = Node.load(old_parent_id)
    new_parent = Node.load(new_parent_id)

    old_doc_type = '{}_file'.format(get_doctype_from_node(old_parent))
    new_doc_type = '{}_file'.format(get_doctype_from_node(new_parent))

    # Try to reuse already indexed document.
    if old_parent.is_public and not content:
        file_body = retrieve(old_file_node._id, old_parent_id, old_doc_type, index=index)
        file_body['parent'] = new_parent_id
        file_body['path'] = new_file_node_id

    else:
        file_node = old_file_node
        file_body = build_file_body(file_node, parent=new_parent, content=content)

    if new_parent.is_public:
        index_doc(
            id=new_file_node_id,
            parent_id=new_parent_id,
            doc_type=new_doc_type,
            body=file_body,
            index=index,
        )


@file_util.require_file_indexing
def move_file(file_node, new_file_node_id, old_parent_id, new_parent_id, content=None, index=None):
    """ Alter search index to reflect the moving of a file to a new location.

    :param file_node: filenode that was moved.
    :param new_file_node_id: the new guid of the filenode.
    :param old_parent_id: the guid of the filenode's pre-move parent.
    :param new_parent_id: the guid of the filenode's post-move parent.
    :param content: the text content of the file associated with the filenode.
    """

    index = index or INDEX
    old_parent = Node.load(old_parent_id)
    new_parent = Node.load(new_parent_id)

    old_doc_type = '{}_file'.format(get_doctype_from_node(old_parent))
    new_doc_type = '{}_file'.format(get_doctype_from_node(new_parent))

    # Try to reuse already indexed document.
    if old_parent.is_public:
        file_body = retrieve(file_node._id, old_parent_id, old_doc_type, index=index)
        file_body['parent'] = new_parent_id
        file_body['path'] = new_file_node_id

    else:
        file_body = build_file_body(file_node, parent=new_parent, content=content)
        file_body['path'] = new_file_node_id

    if new_parent.is_public:
        index_doc(
            id=new_file_node_id,
            parent_id=new_parent_id,
            doc_type=new_doc_type,
            body=file_body,
            index=index,
        )

    if old_parent.is_public:
        delete_from(file_node, old_parent_id, index=index)
