from .model import Node, NodeLog, NodeWikiPage
from framework.forms.utils import sanitize
from framework.mongo.utils import from_mongo

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
            raise RuntimeError("unexpected opcode")
    return ''.join(output)


def new_node(category, title, user, description=None, project=None):
    # tag: database
    category = category.strip().lower()
    title = sanitize(title.strip())
    if description:
        description = sanitize(description.strip())

    the_node = Node(
        title=title,
        category=category,
        creator=user,
        description=description,
        project=project,
    )

    the_node.save()

    return the_node


def get_wiki_page(project, node, wid):
    if node and node.wiki and wid in node.wiki:
        pw = NodeWikiPage.load(node.wiki_page_current[wid])
    elif project and project.wiki and wid in project.wiki:
        pw = NodeWikiPage.load(project.wiki_page_current[wid])
    else:
        pw = None

    return pw


def get_node(id):
    return Node.load(id)

template_name_replacements = {
    ('.txt', ''),
    ('_', ' '),
}


def clean_template_name(template_name):
    template_name = from_mongo(template_name)
    for replacement in template_name_replacements:
        template_name = template_name.replace(*replacement)
    return template_name
