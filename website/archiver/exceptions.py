from website.archiver import mails
from website.archiver.utils import delete_registration_tree
from website import settings
from website.mails import send_mail

def send_archiver_mail(*args, **kwargs):
    """A proxy to facilitate unit testing"""
    send_mail(*args, **kwargs)

class ArchiverError(Exception):
    pass

class ArchiverSizeExceeded(ArchiverError):
    def __init__(self, src, dst, user, stat_result, *args, **kwargs):
        """Capture and respond to an archive task that is failed due to disk usage constraints.
        Deletes the failed registration.

        :param src: Node being registered
        :param dst: registration Node
        :param user: registration initiator
        :param stat_result: AggregateStatResult of Node addon metadata
        """
        super(ArchiverSizeExceeded, self).__init__(*args, **kwargs)
        send_archiver_mail(
            to_addr=settings.SUPPORT_EMAIL,
            mail=mails.ARCHIVE_SIZE_EXCEEDED_DESK,
            user=user,
            src=src,
            stat_result=stat_result
        )
        send_archiver_mail(
            to_addr=user.username,
            mail=mails.ARCHIVE_SIZE_EXCEEDED_USER,
            user=user,
            src=src,
            stat_result=stat_result,
            mimetype='html',
        )
        delete_registration_tree(dst)

class ArchiverCopyError(ArchiverError):

    def __init__(self, src, dst, user, results, *args, **kwargs):
        """Capture and respond to an archive task that is failed when one or more copy
        requests to the WaterButler API fail. Deletes the failed registration.

        :param src: Node being registered
        :param dst: registration Node
        :param user: registration initiator
        :param results: collected statuses and errors returned from the WaterButler API
        """
        super(ArchiverCopyError, self).__init__(*args, **kwargs)
        send_archiver_mail(
            to_addr=settings.SUPPORT_EMAIL,
            mail=mails.ARCHIVE_COPY_ERROR_DESK,
            user=user,
            src=src,
            results=results,
        )
        send_archiver_mail(
            to_addr=user.username,
            mail=mails.ARCHIVE_COPY_ERROR_USER,
            user=user,
            src=src,
            results=results,
            mimetype='html',
        )
        delete_registration_tree(dst)
