# -*- coding: utf-8 -*-

import furl
import httplib as http
import json
import urllib

from lxml import etree
import requests

from framework.auth import User
from framework.auth import authenticate
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
        super(CasTokenError, self).__init__(http.BAD_REQUEST, message)


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

    def get_login_url(self, service_url, username=None, verification_key=None):
        url = furl.furl(self.BASE_URL)
        url.path.segments.append('login')
        url.args['service'] = service_url
        if username and verification_key:
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
    return '/login?service={}&auto=true'.format(urllib.quote(redirect_url, safe='~()*!.\''))


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
    :return:
    """

    service_furl = furl.furl(service_url)
    if 'ticket' in service_furl.args:
        service_furl.args.pop('ticket')
    client = get_client()
    cas_resp = client.service_validate(ticket, service_furl.url)
    if cas_resp.authenticated:
        user = User.load(cas_resp.user)
        # if we successfully authenticate and a verification key is present, invalidate it
        if user.verification_key:
            user.verification_key = None
            user.save()
        return authenticate(user, access_token=cas_resp.attributes['accessToken'], response=redirect(service_furl.url))
    # Ticket could not be validated, unauthorized.
    return redirect(service_furl.url)
