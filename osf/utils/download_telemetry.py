import functools
import ipaddress
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

# Hops that are never the person downloading: internal networks the request passes
# through on its way in, and the ranges Google's load balancers connect to backends
# from. Deployment-specific addresses (the LB's own public IP, say) belong in
# settings.TRUSTED_PROXY_CIDRS rather than here.
PROXY_NETWORKS = tuple(
    ipaddress.ip_network(cidr)
    for cidr in (
        '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16',   # RFC1918
        '127.0.0.0/8', '::1/128',                          # loopback
        '169.254.0.0/16', 'fe80::/10',                     # link-local
        'fc00::/7',                                        # IPv6 ULA
        '130.211.0.0/22', '35.191.0.0/16',                 # GCP LB -> backend ranges
    )
)


def get_client_ip(remote_addr, forwarded_for=''):
    """The address of whoever is actually downloading, not of our own infrastructure.

    ``remote_addr`` is just the peer that opened the TCP connection -- behind the load
    balancer that's the balancer itself, which is how every telemetry row ended up
    carrying the same LB address. The real client survives in ``X-Forwarded-For``, so
    walk that chain right to left and return the first hop that isn't a proxy
    (:data:`PROXY_NETWORKS` plus ``settings.TRUSTED_PROXY_CIDRS``).

    Right to left matters: the left end of the header arrives from the client and can
    say anything, so it is only believed once every hop to its right checked out. If
    the whole chain is internal (or there's no header at all) this falls back to the
    leftmost parseable address, which is today's behaviour.

    Returns a validated address or None -- never garbage, the column is an inet.
    """
    candidates = [part.strip() for part in (forwarded_for or '').split(',') if part.strip()]
    if remote_addr and remote_addr.strip():
        candidates.append(remote_addr.strip())

    parsed = [ip for ip in (_parse_ip(raw) for raw in candidates) if ip is not None]
    if not parsed:
        return None

    proxy_networks = PROXY_NETWORKS + _configured_proxy_networks()
    for ip in reversed(parsed):
        if not any(ip in network for network in proxy_networks):
            return str(ip)
    return str(parsed[0])


def _parse_ip(raw):
    """One X-Forwarded-For token as an address, or None -- proxies put all sorts of
    junk in that header ('unknown', obfuscated entries), and junk just gets skipped."""
    value = raw.strip()
    if value.startswith('[') and ']' in value:  # bracketed IPv6, possibly with a port
        value = value[1:value.index(']')]
    try:
        return ipaddress.ip_address(value)
    except ValueError:
        return None


def _configured_proxy_networks():
    """Deployment-specific proxy CIDRs (the LB's public address), straight from settings.

    Parsed per call so a bad entry can be fixed by config alone; an invalid CIDR is
    logged and skipped rather than taking the capture down with it.
    """
    from website import settings

    networks = []
    for cidr in getattr(settings, 'TRUSTED_PROXY_CIDRS', None) or []:
        try:
            networks.append(ipaddress.ip_network(cidr, strict=False))
        except ValueError:
            logger.warning('Ignoring invalid CIDR in TRUSTED_PROXY_CIDRS: %r', cidr)
    return tuple(networks)


def classify_download_channel(source_area, is_api_token=False):
    """Best server-side guess at where a download came from, for the dashboard's
    frontend-vs-API split.

    Deliberately does NOT trust the User-Agent — browsers and bots alike set it (the QA
    screenshots showed automated traffic sending ordinary Chrome UA strings). The signals
    here are ones the client can't fake into looking like the OSF UI:

    - an API/OAuth bearer token means a programmatic client (a browser navigating a
      download link never sends one) -> API
    - otherwise a ``source`` tag means the request came from an OSF UI download link,
      which only our own frontend adds -> FRONTEND
    - everything else (direct links, crawlers) -> OTHER

    Only single-file downloads, captured at the redirect view, can see the token. Zip
    downloads are captured from the WaterButler callback, which doesn't carry the original
    request's auth, so their API traffic can't be told from OTHER — they still split
    FRONTEND vs not by the source tag. ``is_api_token`` is always False for zips.
    """
    from osf.models import DownloadEvent

    if is_api_token:
        return DownloadEvent.API
    if source_area:
        return DownloadEvent.FRONTEND
    return DownloadEvent.OTHER


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
    storage_provider='',
    storage_region_id=None,
    zip_completed=None,
    status_code=None,
    user_guid=None,
    ip=None,
    user_agent='',
    source_area='',
    download_channel='',
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
        status_code=status_code,
        storage_provider=_truncate(storage_provider, 32),
        storage_region=_truncate(storage_region, 64),
        user_region=_truncate(derive_user_region(tz, user, storage_region), 64),
        ip=ip or None,
        # capped: the User-Agent comes off the request, so it's client-controlled
        user_agent=_truncate(user_agent, 512),
        source_area=_truncate(source_area, 128),
        download_channel=_truncate(download_channel, 16),
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
