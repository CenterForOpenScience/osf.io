from website.settings import DOMAIN as OSF_DOMAIN
from website.project.model import User
from furl import furl


def serialize_comment(comment):
    reports = [
        serialize_report(user, report)
        for user, report in comment.reports.iteritems()
    ]
    author_abs_url = furl(OSF_DOMAIN)
    author_abs_url.path.add(comment.user.url)

    return {
        'id': comment._id,
        'author': User.load(comment.user._id),
        'author_id': comment.user._id,
        'author_path': author_abs_url.url,
        'date_created': comment.date_created,
        'date_modified': comment.date_modified,
        'content': comment.content,
        'has_children': bool(getattr(comment, 'commented', [])),
        'modified': comment.modified,
        'is_deleted': comment.is_deleted,
        'spam_status': comment.spam_status,
        'reports': reports,
        'node': comment.node,
        'category': reports[0]['category'],
    }


def serialize_report(user, report):
    return {
        'reporter': User.load(user),
        'category': report.get('category', None),
        'reason': report.get('text', None),
    }
