from website.project.model import User


def serialize_comment(comment):
    reports = [
        serialize_report(user, report)
        for user, report in comment.reports.iteritems()
    ]

    return {
        'id': comment._id,
        'author': User.load(comment.user._id),
        'date_created': comment.date_created,
        'date_modified': comment.date_modified,
        'content': comment.content,
        'has_children': bool(getattr(comment, 'commented', [])),
        'modified': comment.modified,
        'is_deleted': comment.is_deleted,
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
