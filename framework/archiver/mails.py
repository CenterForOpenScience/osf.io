from website.mails import Mail

def generate_stat_report(stat_result):
    out = []
    tmpl = """
    -------------------------\n
    {addon}: \n
    \t- Archive size: {size}\n
    \t- Num. files: {nfiles}\n
    \t- Node settings pk: {id}\n
    """
    for key, target in stat_result.targets.iteritems():
        out.append(tmpl.format(
            addon=target.target_name,
            size=target.disk_usage,
            nfiles=target.num_files,
            id=target.target_id,
        ))
    return ''.join(out)

def generate_copy_report(report):
    out = []
    tmpl = """
    -------------------------\n
    {addon}: \n
    \t- copy status: {status},
    \t- errors: \n
       ${errors}\n
    """
    for provider, value in report.iteritems():
        out.append(tmpl.format(
            addon=provider,
            status=value['status'],
            errors='--------\n'.join(value['errors']),
        ))
    return ''.join(out)

ARCHIVE_SIZE_EXCEEDED_DESK = Mail(
    'archive_size_exceeded_desk',
    subject="Problem registering '${src}'"
)
ARCHIVE_SIZE_EXCEEDED_USER = Mail(
    'archive_size_exceeded_user',
    subject="Problem registering '${src}'"
)

ARCHIVE_COPY_ERROR_DESK = Mail(
    'archive_copy_error_desk',
    subject="Problem registering '${src}'"
)
ARCHIVE_COPY_ERROR_USER = Mail(
    'archive_copy_error_user',
    subject="Problem registering '${src}'"
)
