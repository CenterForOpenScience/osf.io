from Framework import *
from .Model import *

import datetime

import difflib
def show_diff(seqm):
    """Unify operations between two compared strings
seqm is a difflib.SequenceMatcher instance whose a & b are strings"""
    output= []
    insert_el = '<span style="background:#4AA02C; font-size:1.5em; ">'
    ins_el_close = '</span>'
    del_el = '<span style="background:#D16587; font-size:1.5em;">'
    del_el_close = '</span>'
    for opcode, a0, a1, b0, b1 in seqm.get_opcodes():
        if opcode == 'equal':
            output.append(seqm.a[a0:a1])
        elif opcode == 'insert':
            output.append(insert_el + seqm.b[b0:b1] + ins_el_close)
        elif opcode == 'delete':
            output.append(del_el + seqm.a[a0:a1] + del_el_close)
        elif opcode == 'replace':
            output.append(del_el + seqm.a[a0:a1] + del_el_close + insert_el + seqm.b[b0:b1] + ins_el_close)
        else:
            raise RuntimeError, "unexpected opcode"
    return ''.join(output)

def new_project(title, description, user):
    project = new_node('project', title, user, description)
    project.add_log('project_created', 
        params={
            'project':project.id,
        },
        user=user,
        log_date=project.date_created
    )
    return project

def new_node(category, title, user, description=None, project=None):
    # tag: database
    category = category.strip().lower()
    title = title.strip()
    if description:
        description = description.strip()
    
    new_node = Node(category=category)
    new_node.title=title
    new_node.description=description
    new_node.is_public=False
    new_node.generate_keywords()
    
    new_node.creator = user
    new_node.optimistic_insert()
    new_node.contributors.append(user)
    new_node.contributor_list.append({'id':user.id})
    new_node.save()

    if project:
        project.nodes.append(new_node)
        project.save()
        new_node.add_log('node_created', 
            params={
                'node':new_node.id,
                'project':project.id,
            }, 
            user=user,
            log_date=new_node.date_created
        )

    return new_node

def get_wiki_page(project, node, wid):
    if node and node.wiki and wid in node.wiki:
        pw = NodeWikiPage.load(node.wiki_page_current[wid])
    elif project and project.wiki and wid in project.wiki:
        pw = NodeWikiPage.load(project.wiki_page_current[wid])
    else:
        pw = None

    return pw

def getNode(id):
    return Node.load(id)

def watchNode(id, uid):
    user = getUser(id=uid)
    project = Node.load(id)
    if not user.watchingNodes:
        user.watchingNodes = []
    else:
        if ref('projects', id) in user.watchingNodes:
            return False
    user.watchingNodes.append(ref('projects', id, backref=(project, "watchingUsers")))
    user.save()
    return True

def get_file_tree(node_to_use, user):
    tree = []
    for node in node_to_use.nodes.objects():
        if not node.is_deleted:
            tree.append(get_file_tree(node, user))

    if node_to_use.is_contributor(user):
        for i,v in node_to_use.files_current.items():
            v = NodeFile.load(v)
            tree.append(v)

    return (node_to_use, tree)