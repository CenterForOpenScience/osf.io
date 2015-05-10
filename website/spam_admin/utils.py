from framework.auth.utils import privacy_info_handle
from modularodm import Q
from framework.utils import iso8601format
from datetime import datetime
import requests
import json
from website import settings
from .spam_admin_settings import SPAM_ASSASSIN_URL, SPAM_ASSASSIN_TEACHING_URL
###################################### GENERAL  ########################################################

def human_readable_date(datetimeobj):
    return datetimeobj.strftime("%b %d, %Y")

#################################  COMMENTS #########################################################
def serialize_comment(comment):

    anonymous = False
    return {
        'author': {
            'url': privacy_info_handle(comment.user.url, anonymous),
            'name': privacy_info_handle(
                comment.user.fullname, anonymous, name=True
            ),
        },
        'dateCreated': human_readable_date(comment.date_created),
        'dateModified': human_readable_date(comment.date_modified),
        'content': comment.content,
        'hasChildren': bool(getattr(comment, 'commented', [])),
        'project': comment.node.title,
        'project_url': comment.node.url,
        'cid': comment._id
    }

def serialize_comments(comments, amount):
    count = 0
    out = []
    for comment in comments:
        out.append(serialize_comment(comment))
        count += 1
        if count >= amount:
            break
    return out


def train_spam(comment, is_spam):
    """ Serialize and send request to spam assassin
    """
    if not settings.SPAM_ASSASSIN:
            return False
    try:
        data = {
            'message': comment.content,
            'email': comment.user.emails[0] if len(comment.user.emails) > 0 else None,
            'date': str(datetime.utcnow()),
            'author': comment.user.fullname,
            'project_title': comment.node.title,
            'is_spam': is_spam
        }

        resp = requests.post(SPAM_ASSASSIN_TEACHING_URL, data=json.dumps(data))

        if resp.text == "Learned":
            return True
        return False
    except:
        return False

def is_spam(comment):
    try:
        if not settings.SPAM_ASSASSIN:
            return False
        data = {
            'message': comment.content,
            'email': comment.user.emails[0] if len(comment.user.emails) > 0 else None,
            'date': str(datetime.utcnow()),
            'author': comment.user.fullname,
            'project_title': comment.node.title,
        }

        resp = requests.post(SPAM_ASSASSIN_URL, data=json.dumps(data))

        if resp.text == "SPAM":
            return True

        return False
    except:

        return False
######################################## PROJECTS ######################################################
def serialize_projects(projects, amount):
    count = 0
    out = []
    for project in projects:
        out.append(serialize_project(project))
        count += 1
        if count >= amount:
            break
    return out

def serialize_project(project):
    from website.addons.wiki.model import NodeWikiPage
    return {
        'wikis': [
            {
                'content': wiki.content if len(wiki.content) < 1000 else wiki.content[:1000] + " ...",
                'page_name': wiki.page_name,
                'date': human_readable_date(wiki.date),
                'url': wiki.url
            }
            for wiki in NodeWikiPage.find(Q('node', 'eq', project))
        ],
        'tags': [tag._id for tag in project.tags],
        'title': project.title,
        'description': project.description or '',
        'url': project.url,
        'date_modified': human_readable_date(project.logs[-1].date) if project.logs else '',
        'author': {
            'email': project.creator.emails,
            'name': project.creator.fullname,
        },
        'pid': project._id,
        'components': [serialize_project(component) for component in project.nodes]
    }

def _format_spam_node_data(node):
    from website.addons.wiki.model import NodeWikiPage
    from website.views import serialize_log

    logs = []
    for log in reversed(node.logs):
        if log:
            logs.append(serialize_log(log))

    content = {
        'wikis': [wiki.content for wiki in NodeWikiPage.find(Q('node', 'eq', node))],
        'logs': logs,
        'tags': [tag._id for tag in node.tags],
        'components': str([_format_spam_node_data(component) for component in node.nodes])
    }
    data = {
        'message': content,
        'project_title': node.title,
        'category': node.category_display,
        'description': node.description or '',
        'url': node.url,
        'absolute_url': node.absolute_url,
        'date_created': iso8601format(node.date_created),
        'date_modified': iso8601format(node.logs[-1].date) if node.logs else '',
        'date': iso8601format(node.logs[-1].date) if node.logs else '',
        'tags': [tag._id for tag in node.tags],
        'is_registration': node.is_registration,
        'registered_from_url': node.registered_from.url if node.is_registration else '',
        'registered_date': iso8601format(node.registered_date) if node.is_registration else '',
        'registration_count': len(node.node__registrations),
        'is_fork': node.is_fork,
        'forked_from_id': node.forked_from._primary_key if node.is_fork else '',
        'forked_from_display_absolute_url': node.forked_from.display_absolute_url if node.is_fork else '',
        'forked_date': iso8601format(node.forked_date) if node.is_fork else '',
        'fork_count': len(node.node__forked.find(Q('is_deleted', 'eq', False))),
        'templated_count': len(node.templated_list),
        'watched_count': len(node.watchconfig__watched),
        'private_links': [x.to_json() for x in node.private_links_active],
        'points': len(node.get_points(deleted=False, folders=False)),
        'comment_level': node.comment_level,
        'has_comments': bool(getattr(node, 'commented', [])),
        'has_children': bool(getattr(node, 'commented', False)),
        'author': node.creator.fullname,
        'email': node.creator.emails,
    }
    return data

def _project_is_spam(node):
    if not settings.SPAM_ASSASSIN:
            return False
    try:
        data = _format_spam_node_data(node)
        res = requests.post(SPAM_ASSASSIN_URL, data=json.dumps(data))
        if res.text == "SPAM":
            return True
        return False
    except:
        return False

def train_spam_project(project, is_spam):
    if not settings.SPAM_ASSASSIN:
            return False
    try:
        serialized_project = _format_spam_node_data(project)
        serialized_project['is_spam'] = is_spam
        r = requests.post(SPAM_ASSASSIN_TEACHING_URL, data=json.dumps(serialized_project))
        if r.text == "Learned":
            return True
        return False
    except:
        return False
