from website.mails import Mail

ARCHIVE_SIZE_EXCEEDED_DESK = Mail(
    'archive_size_exceeded_desk',
    subject="Problem registering ${src.title}"
)
ARCHIVE_SIZE_EXCEEDED_USER = Mail(
    'archive_size_exceeded_user',
    subject="Problem registering ${src.title}"
)

ARCHIVE_COPY_ERROR_DESK = Mail(
    'archive_copy_error_desk',
    subject="Problem registering ${src.title}"
)
ARCHIVE_COPY_ERROR_USER = Mail(
    'archive_copy_error_user',
    subject="Problem registering ${src.title}"
)

ARCHIVE_SUCCESS = Mail(
    'archive_success',
    subject="Registration of ${src.title} complete"
)
