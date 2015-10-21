from website.project.model import Comment, User
from website.profile.utils import serialize_user
from modularodm import Q


def serialize_comment(comment):
    comment = {
        'id': comment._id,
        'author': serialize_user(comment.user),
        'date_created': comment.date_created.isoformat(),
        'date_modified': comment.date_modified.isoformat(),
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


def serialize_comments():
    query = Q('reports', 'ne', {})
    return [
        serialize_comment(c)
        for c in Comment.find(query)
    ]


def serialize_reports(reports):
    return [
        serialize_report(user, report)
        for user, report in reports.iteritems()
    ]


def serialize_report(user, report):
    return {
        'reporter': serialize_user(User.load(user)),
        'category': report.get('category', None),
        'reason': report.get('text', None),
    }
