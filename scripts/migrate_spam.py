from website.project.model import Comment


def migrate_comment(comment):
    output = 'Comment fine.'
    try:
        temp = comment.spam_status
    except:
        if len(comment.reports) > 0:
            comment.spam_status = Comment.FLAGGED
    if comment.spam_status not in (Comment.FLAGGED, Comment.SPAM,
                                   Comment.UNKNOWN, Comment.HAM):
        comment.spam_status = Comment.UNKNOWN
    try:
        temp = comment.latest_report
    except:
        date = None
        for user, report in comment.reports.iteritems():
            report_date = report.get('date')
            if date is None or report_date > date:
                date = report_date
        comment.latest_report = date
    comment.save()


def main():
    comments = Comment.find()
    for comment in comments:
        migrate_comment(comment)


if __name__ == '__main__':
    main()
