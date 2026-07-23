import functools
import logging

from addons.osfstorage.settings import DEFAULT_REGION_NAME
from framework.celery_tasks import app
from framework.postcommit_tasks.handlers import enqueue_postcommit_task

logger = logging.getLogger(__name__)

# Set on every user until they pick something in their profile, so it says nothing
# about where they actually are.
UNSET_USER_TIMEZONE = 'Etc/UTC'

# Identifiers worth having in the log line to track a failure back to one download.
# Deliberately excludes the IP.
LOGGED_CONTEXT_KEYS = ('download_type', 'resource_guid', 'file_id', 'user_guid')


def never_breaks_downloads(fn):
    """Swallow and log anything this raises.

    Wraps the whole capture, not just the write — gathering the values is as capable of
    raising as storing them is, and neither is a reason for a download to fail.
    """
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            # exc_info carries the traceback; the rest names the failure and which
            # download it was, so a report is actionable without reproducing it.
            logger.exception(
                'Failed to record a download event in %s: %s: %s [%s]',
                fn.__name__,
                type(exc).__name__,
                exc,
                ', '.join(
                    f'{key}={kwargs[key]!r}'
                    for key in LOGGED_CONTEXT_KEYS
                    if kwargs.get(key)
                ) or 'no context',
            )
    return wrapped


@never_breaks_downloads
def record_download(**kwargs):
    """Enqueue a :class:`DownloadEvent` write."""
    enqueue_postcommit_task(write_download_event, (), kwargs, celery=True)


@app.task(max_retries=5, default_retry_delay=60)
def write_download_event(
    download_type,
    resource_guid='',
    path='',
    file_id=None,
    version_identifier=None,
    size_bytes=None,
    storage_region_id=None,
    zip_completed=None,
    user_guid=None,
    ip=None,
    source_area='',
    tz='',
):
    """Resolve the expensive bits and write one row.

    Callers hand over identifiers rather than loaded objects so that the download request
    itself does no extra queries — everything that needs a lookup is resolved here.
    """
    from osf.models import BaseFileNode, DownloadEvent, OSFUser

    user = OSFUser.load(user_guid) if user_guid else None
    file_node = BaseFileNode.load(file_id) if file_id else None
    file_version = _load_file_version(file_node, version_identifier)

    if file_version is not None:
        if size_bytes is None:
            size_bytes = file_version.size
        if storage_region_id is None:
            storage_region_id = file_version.region_id

    storage_region = _region_name(storage_region_id) or _resource_region_name(resource_guid)

    if not path and file_node is not None:
        path = getattr(file_node, 'materialized_path', '') or ''

    DownloadEvent.objects.create(
        download_type=download_type,
        resource_guid=_truncate(resource_guid, 255),
        path=path or '',
        size_bytes=size_bytes if size_bytes is not None and size_bytes >= 0 else None,
        zip_completed=zip_completed,
        storage_region=_truncate(storage_region, 64),
        user_region=_truncate(derive_user_region(tz, user, storage_region), 64),
        ip=ip or None,
        source_area=_truncate(source_area, 128),
        user=user,
    )


def derive_user_region(tz, user, storage_region):
    """Best available guess at where the user is, most to least trustworthy.

    The live browser timezone is the only real signal; the rest are fallbacks so the
    dashboard isn't mostly blank.  An empty string means we genuinely don't know, which
    is more useful than a wrong guess.
    """
    if tz:
        return tz

    profile_timezone = getattr(user, 'timezone', '')
    if profile_timezone and profile_timezone != UNSET_USER_TIMEZONE:
        return profile_timezone

    # Everything defaults to the US region, so it only tells us something when it's been
    # deliberately changed.
    if storage_region and storage_region != DEFAULT_REGION_NAME:
        return storage_region

    return ''


def _load_file_version(file_node, version_identifier):
    """The version that was served, for its size and region."""
    if file_node is None:
        return None

    from osf.models import FileVersion

    versions = FileVersion.objects.filter(basefilenode=file_node)
    if version_identifier:
        return versions.filter(identifier=version_identifier).first()
    return versions.order_by('-created').first()


def _region_name(region_id):
    if not region_id:
        return ''

    from addons.osfstorage.models import Region

    region = Region.objects.filter(id=region_id).first()
    return region.name if region else ''


def _resource_region_name(resource_guid):
    """Where a zip was served from — zips have no single file version to read it off."""
    if not resource_guid:
        return ''

    from osf.models import Guid

    resource, _ = Guid.load_referent(resource_guid)
    region = getattr(resource, 'osfstorage_region', None)
    return getattr(region, 'name', '') or ''


def _truncate(value, max_length):
    """Keep user-controllable values inside their column.

    ``source`` and ``tz`` arrive off the query string, so they're whatever the caller
    put there.
    """
    return (value or '')[:max_length]
