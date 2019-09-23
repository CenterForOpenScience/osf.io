# -*- coding: utf-8 -*-

import furl
from rest_framework import status as http_status
import json
from future.moves.urllib.parse import quote

from lxml import etree
import requests

from framework.auth import authenticate, external_first_login_authenticate
from framework.auth.core import get_user, generate_verification_key
from framework.flask import redirect
from framework.exceptions import HTTPError
from website import settings


class CasError(HTTPError):
    """General CAS-related error."""

    pass


class CasHTTPError(CasError):
    """Error raised when an unexpected error is returned from the CAS server."""

    def __init__(self, code, message, headers, content):
        super(CasHTTPError, self).__init__(code, message)
        self.headers = headers
        self.content = content

    def __repr__(self):
        return ('CasHTTPError({self.message!r}, {self.code}, '
                'headers={self.headers}, content={self.content!r})').format(self=self)

    __str__ = __repr__


class CasTokenError(CasError):
    """Raised if an invalid token is passed by the client."""

    def __init__(self, message):
        super(CasTokenError, self).__init__(http_status.HTTP_400_BAD_REQUEST, message)


class CasResponse(object):
    """A wrapper for an HTTP response returned from CAS."""

    def __init__(self, authenticated=False, status=None, user=None, attributes=None):
        self.authenticated = authenticated
        self.status = status
        self.user = user
        self.attributes = attributes or {}


class CasClient(object):
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

        url = furl.furl(self.BASE_URL)
        url.path.segments.append('login')
        url.args['service'] = service_url
        if campaign:
            url.args['campaign'] = campaign
        elif username and verification_key:
            url.args['username'] = username
            url.args['verification_key'] = verification_key
        return url.url

    def get_logout_url(self, service_url):
        url = furl.furl(self.BASE_URL)
        url.path.segments.append('logout')
        url.args['service'] = service_url
        return url.url

    def get_profile_url(self):
        url = furl.furl(self.BASE_URL)
        url.path.segments.extend(('oauth2', 'profile',))
        return url.url

    def get_auth_token_revocation_url(self):
        url = furl.furl(self.BASE_URL)
        url.path.segments.extend(('oauth2', 'revoke'))
        return url.url

    def service_validate(self, ticket, service_url):
        """
        Send request to CAS to validate ticket.

        :param str ticket: CAS service ticket
        :param str service_url: Service URL from which the authentication request originates
        :rtype: CasResponse
        :raises: CasError if an unexpected response is returned
        """

        url = furl.furl(self.BASE_URL)
        url.path.segments.extend(('p3', 'serviceValidate',))
        url.args['ticket'] = ticket
        url.args['service'] = service_url

        resp = requests.get(url.url)
        if resp.status_code == 200:
            return self._parse_service_validation(resp.content)
        else:
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
            'Authorization': 'Bearer {}'.format(access_token),
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
        resp.status = unicode(auth_doc.xpath('local-name()'))
        if (resp.status == 'authenticationSuccess'):
            resp.authenticated = True
            resp.user = unicode(auth_doc.xpath('string(./cas:user)', namespaces=doc.nsmap))
            attributes = auth_doc.xpath('./cas:attributes/*', namespaces=doc.nsmap)
            for attribute in attributes:
                resp.attributes[unicode(attribute.xpath('local-name()'))] = unicode(attribute.text)
            scopes = resp.attributes.get('accessTokenScope')
            resp.attributes['accessTokenScope'] = set(scopes.split(' ') if scopes else [])
        else:
            resp.authenticated = False
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

    service_furl = furl.furl(service_url)
    # `service_url` is guaranteed to be removed of `ticket` parameter, which has been pulled off in
    # `framework.sessions.before_request()`.
    if 'ticket' in service_furl.args:
        service_furl.args.pop('ticket')
    client = get_client()
    cas_resp = client.service_validate(ticket, service_furl.url)
    if cas_resp.authenticated:
        user, external_credential, action = get_user_from_cas_resp(cas_resp)
        # user found and authenticated
        if user and action == 'authenticate':
            # if we successfully authenticate and a verification key is present, invalidate it
            if user.verification_key:
                user.verification_key = None
                user.save()

            # if user is authenticated by external IDP, ask CAS to authenticate user for a second time
            # this extra step will guarantee that 2FA are enforced
            # current CAS session created by external login must be cleared first before authentication
            if external_credential:
                user.verification_key = generate_verification_key()
                user.save()
                return redirect(get_logout_url(get_login_url(
                    service_url,
                    username=user.username,
                    verification_key=user.verification_key
                )))

            # if user is authenticated by CAS
            # TODO [CAS-27]: Remove Access Token From Service Validation
            return authenticate(
                user,
                cas_resp.attributes.get('accessToken', ''),
                redirect(service_furl.url)
            )
        # first time login from external identity provider
        if not user and external_credential and action == 'external_first_login':
            from website.util import web_url_for
            # orcid attributes can be marked private and not shared, default to orcid otherwise
            fullname = u'{} {}'.format(cas_resp.attributes.get('given-names', ''), cas_resp.attributes.get('family-name', '')).strip()
            # TODO [CAS-27]: Remove Access Token From Service Validation
            user = {
                'external_id_provider': external_credential['provider'],
                'external_id': external_credential['id'],
                'fullname': fullname,
                'access_token': cas_resp.attributes.get('accessToken', ''),
                'service_url': service_furl.url,
            }
            return external_first_login_authenticate(
                user,
                redirect(web_url_for('external_login_email_get'))
            )
    # Unauthorized: ticket could not be validated, or user does not exist.
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
                return None, None, None
            # cas returns a valid external credential
            user = get_user(external_id_provider=external_credential['provider'],
                            external_id=external_credential['id'])
            # existing user found
            if user:
                return user, external_credential, 'authenticate'
            # user first time login through external identity provider
            else:
                return None, external_credential, 'external_first_login'


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
