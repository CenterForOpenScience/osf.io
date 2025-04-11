import re

from urllib.parse import urljoin

from website import settings

"""
Old workflow uses DraftRegistration.registration_metadata and Registration.registered_meta.
New workflow uses DraftRegistration.registration_responses and Registration.registration_responses.

Both workflows need to be accommodated for the foreseeable future, so writing to one field
needs to write to the other field.

Contains helps for "flatten_registration_metadata" for converting from old to new, and
"expand_registration_responses" for converting from new to old.
"""

# relative urls from the legacy 'nested' format
FILE_VIEW_URL_TEMPLATE = '/project/{node_id}/files/osfstorage/{file_id}'
FILE_VIEW_URL_REGEX = re.compile(r'/(?:project/)?(?P<node_id>\w{5})/files/osfstorage/(?P<file_id>\w{24})')

# use absolute URLs in new 'flattened' format
FILE_HTML_URL_TEMPLATE = urljoin(settings.DOMAIN, '/project/{node_id}/files/osfstorage/{file_id}')
FILE_DOWNLOAD_URL_TEMPLATE = urljoin(settings.DOMAIN, '/download/{file_id}')
