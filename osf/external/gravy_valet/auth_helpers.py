import base64
import hashlib
import hmac
import re
import urllib

from django.utils import timezone

from osf.models import OSFUser, AbstractNode
from osf.utils import permissions as osf_permissions
from website import settings

_AUTH_HEADER_REGEX = re.compile(
    r'^HMAC-SHA256 SignedHeaders=(?P<headers>[\w;-]*)&Signature=(?P<signature>[^\W_]*$)'
)
TIMESTAMP_HEADER = 'X-Authorization-Timestamp'
CONTENT_HASH_HEADER = 'X-Content-SHA256'
USER_HEADER = 'X-Requesting-User-URI'
RESOURCE_HEADER = 'X-Requested-Resource-URI'
PERMISSIONS_HEADER = 'X-Requested-Resource-Permissions'


def _sign_message(message: str, hmac_key: str = None) -> str:
    key = hmac_key or settings.DEFAULT_HMAC_SECRET
    encoded_message = base64.b64encode(message.encode())
    return hmac.new(
        key=key.encode(), digestmod=hashlib.sha256, msg=encoded_message
    ).hexdigest()


def _get_signed_components(
    request_url: str, request_method: str, body: str | bytes, **additional_headers
) -> tuple[list[str], dict[str, str]]:
    parsed_url = urllib.parse.urlparse(request_url)
    if isinstance(body, str):
        body = body.encode()
    content_hash = hashlib.sha256(body).hexdigest() if body else None
    auth_timestamp = timezone.now().isoformat()
    signed_segments = [
        request_method,
        parsed_url.path,
        parsed_url.query,
        auth_timestamp,
        content_hash,
        *additional_headers.values()
    ]
    # Filter out query string and content_hash if none present
    signed_segments = [segment for segment in signed_segments if segment]
    signed_headers = {TIMESTAMP_HEADER: auth_timestamp}
    if content_hash:
        signed_headers[CONTENT_HASH_HEADER] = content_hash
    # order matters, so append additional headers at the end for consistency
    signed_headers.update(additional_headers)
    return signed_segments, signed_headers


def make_permissions_headers(
    requesting_user: OSFUser | None = None,
    requested_resource: AbstractNode | None = None
) -> dict:
    osf_permissions_headers = {}
    if requesting_user:
        osf_permissions_headers[USER_HEADER] = requesting_user.get_semantic_iri()
    if requested_resource:
        osf_permissions_headers[RESOURCE_HEADER] = requested_resource.get_semantic_iri()
        user_permissions = ''
        if requesting_user:
            user_permissions = ';'.join(requested_resource.get_permissions(requesting_user))
        if (not requesting_user or not user_permissions) and requested_resource.is_public:
            user_permissions = osf_permissions.READ
        osf_permissions_headers[PERMISSIONS_HEADER] = user_permissions
    return osf_permissions_headers


def make_gravy_valet_hmac_headers(
    request_url: str,
    request_method: str,
    body: str | bytes = '',
    hmac_key: str | None = None,
    additional_headers: dict | None = None,
) -> dict:

    additional_headers = additional_headers or {}
    signed_string_segments, signed_headers = _get_signed_components(
        request_url, request_method, body, **additional_headers
    )
    signature = _sign_message(
        message='\n'.join(signed_string_segments), hmac_key=hmac_key
    )

    signature_header_fields = ';'.join(signed_headers.keys())
    auth_header_value = (
        f'HMAC-SHA256 SignedHeaders={signature_header_fields}&Signature={signature}'
    )
    return dict(
        **signed_headers,
        Authorization=auth_header_value,
    )


def _reconstruct_string_to_sign_from_request(request, signed_headers: list[str]) -> str:
    parsed_url = urllib.parse.urlparse(request.url)
    signed_segments = [request.method, parsed_url.path]
    if parsed_url.query:
        signed_segments.append(parsed_url.query)
    signed_segments.extend(
        str(request.headers[signed_header]) for signed_header in signed_headers
    )
    return '\n'.join(segment for segment in signed_segments if segment)


def validate_signed_headers(request, hmac_key: str | None = None):
    match = _AUTH_HEADER_REGEX.match(request.headers.get('Authorization', ''))
    if not match:
        raise ValueError(
            'Message was not authorized via valid HMAC-SHA256 signed headers'
        )
    expected_signature = match.group('signature')
    signed_headers = match.group('headers').split(';')

    computed_signature = _sign_message(
        message=_reconstruct_string_to_sign_from_request(
            request, signed_headers=signed_headers
        ),
        hmac_key=hmac_key,
    )
    if not hmac.compare_digest(computed_signature, expected_signature):
        raise ValueError('Could not verify HMAC signed request')

    content_hash = request.headers.get('X-Content-SHA256')
    if content_hash and not hmac.compare_digest(
        content_hash, hashlib.sha256(request.body).hexdigest()
    ):
        raise ValueError('Computed content hash did not match value from headers')
