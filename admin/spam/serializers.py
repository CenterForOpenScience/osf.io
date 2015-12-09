from website.project.model import Comment, User
from website.profile.utils import serialize_user
from modularodm import Q


def serialize_comment(comment, full=False):
    comment = {
        'id': comment._id,
        'author': comment.user,
        'date_created': comment.date_created,
        'date_modified': comment.date_modified,
        'content': comment.content,
        'has_children': bool(getattr(comment, 'commented', [])),
        'modified': comment.modified,
        'is_deleted': comment.is_deleted,
        'reports': serialize_reports(comment.reports),
        'node': comment.node,
    }
    comment.update(
        category=comment['reports'][0]['category'],
    )
    return comment


def retrieve_comment(id, full_user=False):
    return serialize_comment(Comment.load(id), full=full_user)


def serialize_comments():
    query = Q('reports', 'ne', {})
    return map(serialize_comment, Comment.find(query))


def serialize_reports(reports):
    return [
        serialize_report(user, report)
        for user, report in reports.iteritems()
    ]


def serialize_report(user, report):
    return {
        'reporter': User.load(user),
        'category': report.get('category', None),
        'reason': report.get('text', None),
    }
