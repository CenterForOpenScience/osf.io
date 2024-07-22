from furl import furl
from urllib.parse import unquote_plus

from django.utils import timezone
from rest_framework import status as http_status
import json
from urllib.parse import quote

from lxml import etree
import requests

from framework.auth import authenticate, external_first_login_authenticate
from framework.auth.core import get_user, generate_verification_key
from framework.auth.utils import print_cas_log, LogLevel
from framework.celery_tasks.handlers import enqueue_task
from framework.flask import redirect
from framework.exceptions import HTTPError
from website import settings


class CasError(HTTPError):
    """General CAS-related error."""

    pass


class CasHTTPError(CasError):
    """Error raised when an unexpected error is returned from the CAS server."""

    def __init__(self, code, message, headers, content):
        super().__init__(code, message)
        self.headers = headers
        self.content = content

    def __repr__(self):
        return ('CasHTTPError({self.message!r}, {self.code}, '
                'headers={self.headers}, content={self.content!r})').format(self=self)

    __str__ = __repr__


class CasTokenError(CasError):
    """Raised if an invalid token is passed by the client."""

    def __init__(self, message):
        super().__init__(http_status.HTTP_400_BAD_REQUEST, message)


class CasResponse:
    """A wrapper for an HTTP response returned from CAS."""

    def __init__(self, authenticated=False, status=None, user=None, attributes=None):
        self.authenticated = authenticated
        self.status = status
        self.user = user
        self.attributes = attributes or {}


class CasClient:
    """HTTP client for the CAS server."""

    def __init__(self, base_url):
        self.BASE_URL = base_url

    def get_login_url(self, service_url, campaign=None, username=None, verification_key=None):
        """
        Get CAS login url with `service_url` as redirect location. There are three options:
        1. no additional parameters provided -> go to CAS login page
        2. `campaign=institution` -> go to CAS institution login page
        3. `(username, verification_key)` -> CAS will verify this request automatically in background

        :param service_url: redirect url after successful login
        :param campaign: the campaign name, currently 'institution' only
        :param username: the username
        :param verification_key: the verification key
        :return: dedicated CAS login url
        """

        url = furl(self.BASE_URL).add(path='login')
        url.args['service'] = service_url
        if campaign:
            url.args['campaign'] = campaign
        elif username and verification_key:
            url.args['username'] = username
            url.args['verification_key'] = verification_key
        return url.url

    def get_logout_url(self, service_url):
        url = furl(self.BASE_URL).add(path='logout')
        url.args['service'] = service_url
        return url.url

    def get_profile_url(self):
        url = furl(self.BASE_URL).add(path=['oauth2', 'profile'])
        return url.url

    def get_auth_token_revocation_url(self):
        url = furl(self.BASE_URL).add(path=['oauth2', 'revoke'])
        return url.url

    def service_validate(self, ticket, service_url):
        """
        Send request to CAS to validate ticket.

        :param str ticket: CAS service ticket
        :param str service_url: Service URL from which the authentication request originates
        :rtype: CasResponse
        :raises: CasError if an unexpected response is returned
        """

        url = furl(self.BASE_URL).add(path=['p3', 'serviceValidate'])
        url.args['ticket'] = ticket
        url.args['service'] = service_url

        print_cas_log(f'Validating service ticket ["{ticket}"]', LogLevel.INFO)
        resp = requests.get(url.url)
        if resp.status_code == 200:
            print_cas_log(
                f'Service ticket validation response: ticket=[{ticket}], status=[{resp.status_code}]',
                LogLevel.INFO,
            )
            return self._parse_service_validation(resp.content)
        else:
            print_cas_log(
                f'Service ticket validation failed: ticket=[{ticket}], status=[{resp.status_code}]',
                LogLevel.ERROR,
            )
            self._handle_error(resp)

    def profile(self, access_token):
        """
        Send request to get profile information, given an access token.

        :param str access_token: CAS access_token.
        :rtype: CasResponse
        :raises: CasError if an unexpected response is returned.
        """

        url = self.get_profile_url()
        headers = {
            'Authorization': f'Bearer {access_token}',
        }
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            return self._parse_profile(resp.content, access_token)
        else:
            self._handle_error(resp)

    def _handle_error(self, response, message='Unexpected response from CAS server'):
        """Handle an error response from CAS."""
        raise CasHTTPError(
            code=response.status_code,
            message=message,
            headers=response.headers,
            content=response.content,
        )

    def _parse_service_validation(self, xml):
        resp = CasResponse()
        doc = etree.fromstring(xml)
        auth_doc = doc.xpath('/cas:serviceResponse/*[1]', namespaces=doc.nsmap)[0]
        resp.status = str(auth_doc.xpath('local-name()'))
        if (resp.status == 'authenticationSuccess'):
            print_cas_log(f'Service validation succeeded with status: ["{resp.status}"]', LogLevel.INFO)
            resp.authenticated = True
            resp.user = str(auth_doc.xpath('string(./cas:user)', namespaces=doc.nsmap))
            attributes = auth_doc.xpath('./cas:attributes/*', namespaces=doc.nsmap)
            for attribute in attributes:
                resp.attributes[str(attribute.xpath('local-name()'))] = str(attribute.text)
            scopes = resp.attributes.get('accessTokenScope')
            resp.attributes['accessTokenScope'] = set(scopes.split(' ') if scopes else [])
        else:
            print_cas_log(f'Service validation failed with status: ["{resp.status}"]', LogLevel.ERROR)
            resp.authenticated = False
        resp_attributes = [f'({key}: {val})' for key, val in resp.attributes.items()]
        print_cas_log(f'Parsed CAS response: attributes=[{resp_attributes}]', LogLevel.INFO)
        return resp

    def _parse_profile(self, raw, access_token):
        data = json.loads(raw)
        resp = CasResponse(authenticated=True, user=data['id'])
        if data.get('attributes'):
            resp.attributes.update(data['attributes'])
        resp.attributes['accessToken'] = access_token
        resp.attributes['accessTokenScope'] = set(data.get('scope', []))
        return resp

    def revoke_application_tokens(self, client_id, client_secret):
        """Revoke all tokens associated with a given CAS client_id"""
        return self.revoke_tokens(payload={'client_id': client_id, 'client_secret': client_secret})

    def revoke_tokens(self, payload):
        """Revoke a tokens based on payload"""
        url = self.get_auth_token_revocation_url()

        resp = requests.post(url, data=payload)
        if resp.status_code == 204:
            return True
        else:
            self._handle_error(resp)


def parse_auth_header(header):
    """
    Given an Authorization header string, e.g. 'Bearer abc123xyz',
    return a token or raise an error if the header is invalid.

    :param header:
    :return:
    """

    parts = header.split()
    if parts[0].lower() != 'bearer':
        raise CasTokenError('Unsupported authorization type')
    elif len(parts) == 1:
        raise CasTokenError('Missing token')
    elif len(parts) > 2:
        raise CasTokenError('Token contains spaces')
    return parts[1]  # the token


def get_client():
    return CasClient(settings.CAS_SERVER_URL)


def get_login_url(*args, **kwargs):
    """
    Convenience function for getting a login URL for a service.

    :param args: Same args that `CasClient.get_login_url` receives
    :param kwargs: Same kwargs that `CasClient.get_login_url` receives
    """

    return get_client().get_login_url(*args, **kwargs)


def get_institution_target(redirect_url):
    return '/login?service={}&auto=true'.format(quote(redirect_url, safe='~()*!.\''))


def get_logout_url(*args, **kwargs):
    """
    Convenience function for getting a logout URL for a service.

    :param args: Same args that `CasClient.get_logout_url` receives
    :param kwargs: Same kwargs that `CasClient.get_logout_url` receives
    """

    return get_client().get_logout_url(*args, **kwargs)


def get_profile_url():
    """Convenience function for getting a profile URL for a user."""

    return get_client().get_profile_url()


def make_response_from_ticket(ticket, service_url):
    """
    Given a CAS ticket and service URL, attempt to validate the user and return a proper redirect response.

    :param str ticket: CAS service ticket
    :param str service_url: Service URL from which the authentication request originates
    :return: redirect response
    """

    service_furl = furl(service_url)
    # `service_url` is guaranteed to be removed of `ticket` parameter, which has been pulled off in
    # `framework.sessions.before_request()`.
    if 'ticket' in service_furl.args:
        service_furl.remove(args=['ticket'])
    client = get_client()
    cas_resp = client.service_validate(ticket, service_furl.url)
    if cas_resp.authenticated:
        user, external_credential, action = get_user_from_cas_resp(cas_resp)
        user_updates = {}  # serialize updates to user to be applied async
        # user found and authenticated
        if user and action == 'authenticate':
            print_cas_log(
                f'CAS response - authenticating user: user=[{user._id}], '
                f'external=[{external_credential}], action=[{action}]',
                LogLevel.INFO,
            )
            # If users check the TOS consent checkbox via CAS, CAS sets the attribute `termsOfServiceChecked` to `true`
            # and then release it to OSF among other authentication attributes. When OSF receives it, it trusts CAS and
            # updates the user object if this is THE FINAL STEP of the login flow. DON'T update TOS consent status when
            # `external_credential == true` (i.e. w/ `action == 'authenticate'` or `action == 'external_first_login'`)
            # since neither is the final step of a login flow.
            tos_checked_via_cas = cas_resp.attributes.get('termsOfServiceChecked', 'false') == 'true'
            if tos_checked_via_cas:
                user_updates['accepted_terms_of_service'] = timezone.now()
                print_cas_log(f'CAS TOS consent checked: {user.guids.first()._id}, {user.username}', LogLevel.INFO)
            # if we successfully authenticate and a verification key is present, invalidate it
            if user.verification_key:
                user_updates['verification_key'] = None

            # if user is authenticated by external IDP, ask CAS to authenticate user for a second time
            # this extra step will guarantee that 2FA are enforced
            # current CAS session created by external login must be cleared first before authentication
            if external_credential:
                user.verification_key = generate_verification_key()
                user.save()
                print_cas_log(
                    f'CAS response - redirect existing external IdP login to verification key login: user=[{user._id}]',
                    LogLevel.INFO
                )
                return redirect(get_logout_url(unquote_plus(get_login_url(
                    service_url,
                    username=user.username,
                    verification_key=user.verification_key
                ))))

            # if user is authenticated by CAS
            print_cas_log(f'CAS response - finalizing authentication: user=[{user._id}]', LogLevel.INFO)
            return authenticate(user, redirect(service_furl.url), user_updates)
        # first time login from external identity provider
        if not user and external_credential and action == 'external_first_login':
            print_cas_log(
                f'CAS response - first login from external IdP: '
                f'external=[{external_credential}], action=[{action}]',
                LogLevel.INFO,
            )
            from website.util import web_url_for
            # orcid attributes can be marked private and not shared, default to orcid otherwise
            fullname = '{} {}'.format(cas_resp.attributes.get('given-names', ''), cas_resp.attributes.get('family-name', '')).strip()
            user = {
                'external_id_provider': external_credential['provider'],
                'external_id': external_credential['id'],
                'fullname': fullname,
                'service_url': service_furl.url,
            }
            print_cas_log(f'CAS response - creating anonymous session: external=[{external_credential}]', LogLevel.INFO)
            return external_first_login_authenticate(
                user,
                redirect(web_url_for('external_login_email_get'))
            )
    # Unauthorized: ticket could not be validated, or user does not exist.
    print_cas_log('Ticket validation failed or user does not exist. Redirect back to service URL (logged out).', LogLevel.ERROR)
    return redirect(service_furl.url)


def get_user_from_cas_resp(cas_resp):
    """
    Given a CAS service validation response, attempt to retrieve user information and next action.
    The `user` in `cas_resp` is the unique GUID of the user. Please do not use the primary key `id`
    or the email `username`. This holds except for the first step of ORCiD login.

    :param cas_resp: the cas service validation response
    :return: the user, the external_credential, and the next action
    """
    from osf.models import OSFUser
    if cas_resp.user:
        user = OSFUser.load(cas_resp.user)
        # cas returns a valid OSF user id
        if user:
            return user, None, 'authenticate'
        # cas does not return a valid OSF user id
        else:
            external_credential = validate_external_credential(cas_resp.user)
            # invalid cas response
            if not external_credential:
                print_cas_log('CAS response error - missing user or external identity', LogLevel.ERROR)
                return None, None, None
            # cas returns a valid external credential
            user = get_user(external_id_provider=external_credential['provider'],
                            external_id=external_credential['id'])
            # existing user found
            if user:
                # Send to celery the following async task to affiliate the user with eligible institutions if verified
                from framework.auth.tasks import update_affiliation_for_orcid_sso_users
                enqueue_task(update_affiliation_for_orcid_sso_users.s(user._id, external_credential['id']))
                return user, external_credential, 'authenticate'
            # user first time login through external identity provider
            else:
                return None, external_credential, 'external_first_login'
    print_cas_log('CAS response error - `cas_resp.user` is empty', LogLevel.ERROR)
    return None, None, None


def validate_external_credential(external_credential):
    """
    Validate the external credential, a string which is composed of the profile name and the technical identifier
    of the external provider, separated by `#`. Return the provider and id on success.

    :param external_credential: the external credential string
    :return: provider and id

    """
    # wrong format
    if not external_credential or '#' not in external_credential:
        return False

    profile_name, technical_id = external_credential.split('#', 1)

    # invalid external identity provider
    if profile_name not in settings.EXTERNAL_IDENTITY_PROFILE:
        return False

    # invalid external id
    if len(technical_id) <= 0:
        return False

    provider = settings.EXTERNAL_IDENTITY_PROFILE[profile_name]

    return {
        'provider': provider,
        'id': technical_id,
    }
