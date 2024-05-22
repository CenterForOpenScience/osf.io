import base64
import hashlib
import hmac
import re
import typing
import urllib

from django.utils import timezone

from osf.models import OSFUser, AbstractNode
from website import settings

_AUTH_HEADER_REGEX = re.compile(
    r'^HMAC-SHA256 SignedHeaders=(?P<headers>[\w;-]*)&Signature=(?P<signature>[^\W_]*$)'
)


def _sign_message(message: str, hmac_key: str = None) -> str:
    key = hmac_key or settings.DEFAULT_HMAC_KEY
    encoded_message = base64.b64encode(message.encode())
    return hmac.new(
        key=key.encode(), digestmod=hashlib.sha256, msg=encoded_message
    ).hexdigest()


def _get_signed_components(
    request_url: str, request_method: str, body: typing.Union[str, bytes], **additional_headers
) -> typing.Tuple[typing.List[str], typing.Dict[str, str]]:
    parsed_url = urllib.parse.urlparse(request_url)
    if isinstance(body, str):
        body = body.encode()
    content_hash = hashlib.sha256(body).hexdigest() if body else None
    auth_timestamp = timezone.now()
    signed_segments = [
        request_method,
        parsed_url.path,
        parsed_url.query,
        str(auth_timestamp),
        content_hash,
        *additional_headers.values()
    ]
    # Filter out query string and content_hash if none present
    signed_segments = [segment for segment in signed_segments if segment]
    signed_headers = {'X-Authorization-Timestamp': auth_timestamp}
    if content_hash:
        signed_headers['X-Content-SHA256'] = content_hash
    # order matters, so append additional headers at the end
    signed_headers |= additional_headers
    return signed_segments, signed_headers


def make_gravy_valet_hmac_headers(
    request_url: str,
    request_method: str,
    body: typing.Union[str, bytes] = '',
    hmac_key: typing.Optional[str] = None,
    requested_user: typing.Optional[OSFUser] = None,
    requested_resource: typing.Optional[AbstractNode] = None
) -> dict:

    osf_permissions_headers = {}
    if requested_user:
        osf_permissions_headers['X-Curernt-User-URI'] = requested_user.get_semantic_iri()
    if requested_user and requested_resource:
        osf_permissions_headers['X-Requested-Resource-URI'] = requested_resource.get_semantic_iri()
        osf_permissions_headers['X-Requested-Resource-Permissions'] = ';'.join(requested_resource.get_permissions(requested_user))

    signed_string_segments, signed_headers = _get_signed_components(
        request_url, request_method, body, **osf_permissions_headers
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


def _reconstruct_string_to_sign_from_request(request, signed_headers: typing.List[str]) -> str:
    signed_segments = [request.method, request.path]
    query_string = request.META.get('QUERY_STRING')
    if query_string:
        signed_segments.append(query_string)
    signed_segments.extend(
        [str(request.headers[signed_header]) for signed_header in signed_headers]
    )
    return '\n'.join([segment for segment in signed_segments if segment])


def validate_signed_headers(request, hmac_key: typing.Optional[str] = None):
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
