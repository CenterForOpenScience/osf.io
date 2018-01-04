from api.base.settings import OSF_SUPPORT_EMAIL, DOMAIN as OSF_DOMAIN
from osf.models import OSFUser
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
        'author': OSFUser.load(comment.user._id),
        'author_id': comment.user._id,
        'author_path': author_abs_url.url,
        'date_created': comment.created,
        'date_modified': comment.modified,
        'content': comment.content,
        'has_children': bool(getattr(comment, 'commented', [])),
        'modified': comment.edited,
        'is_deleted': comment.is_deleted,
        'spam_status': comment.spam_status,
        'reports': reports,
        'node': comment.node,
        'category': reports[0]['category'],
        'osf_support_email': OSF_SUPPORT_EMAIL,
    }


def serialize_report(user, report):
    return {
        'reporter': OSFUser.load(user),
        'category': report.get('category', None),
        'reason': report.get('text', None),
    }
