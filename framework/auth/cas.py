# -*- coding: utf-8 -*-
import furl
import json
import requests
from lxml import etree

from website import settings

from framework.auth import User
from framework.auth import authenticate
from framework.flask import redirect

class CasError(Exception):
    """General CAS-related error."""
    pass

class CasHTTPError(CasError):
    """Error raised when an unexpected error is returned from the CAS server."""
    def __init__(self, message, status_code, headers):
        super(CasError, self).__init__(message)
        self.status_code = status_code
        self.headers = headers


class CasTokenError(CasError):
    """Raised if an invalid token is passed by the client."""
    pass

class CasResponse(object):
    """A wrapper for an HTTP response returned from CAS."""

    def __init__(self, authenticated=False, status=None, user=None, attributes=None):
        self.authenticated = authenticated
        self.status = status
        self.user = user
        self.attributes = attributes or {}

def parse_auth_header(header):
    """Given a Authorization header string, e.g. 'Bearer abc123xyz', return a token
    or raise an error if the header is invalid.
    """
    parts = header.split()
    if parts[0].lower() != 'bearer':
        raise CasTokenError('Unsupported authorization type')
    elif len(parts) == 1:
        raise CasTokenError('Missing token')
    elif len(parts) > 2:
        raise CasTokenError('Token contains spaces')
    return parts[1]  # the token

class CasClient(object):
    """HTTP client for the CAS server."""

    def __init__(self, base_url):
        self.BASE_URL = base_url

    def get_login_url(self, service_url, auto=False, username=None, password=None, verification_key=None, otp=None):
        url = furl.furl(self.BASE_URL)
        url.path.segments.append('login')
        url.args['service'] = service_url
        if auto:
            url.args['auto'] = 'true'
            if username:
                url.args['username'] = username
            if password:
                url.args['password'] = password
            if verification_key:
                url.args['verification_key'] = verification_key
            if otp:
                url.args['otp'] = otp
        return url.url

    def get_logout_url(self, service_url):
        url = furl.furl(self.BASE_URL)
        url.path.segments.append('logout')
        url.args['service'] = service_url
        return url.url

    def service_validate(self, ticket, service_url):
        """Send request to validate ticket.

        :param str ticket: CAS service ticket.
        :param str service_url: Service URL from which the authentication request
            originates.
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
            self.handle_error(resp)

    def profile(self, access_token):
        """Send request to get profile information, given an access token.

        :param str access_token: CAS access_token.
        :rtype: CasResponse
        :raises: CasError if an unexpected response is returned.
        """
        url = furl.furl(self.BASE_URL)
        url.path.segments.extend(('oauth2', 'profile',))
        headers = {
            'Authorization': 'Bearer {}'.format(access_token),
        }
        resp = requests.get(url.url, headers=headers)
        if resp.status_code == 200:
            return self._parse_profile(resp.content)
        else:
            self.handle_error(resp)

    def handle_error(self, response, message='Unexpected response from CAS server'):
        """Handle an error response from CAS."""
        raise CasHTTPError(
            message,
            status_code=response.status_code,
            headers=response.headers,
        )

    def _parse_service_validation(self, xml):
        resp = CasResponse()
        doc = etree.fromstring(xml)
        auth_doc = doc.xpath('/cas:serviceResponse/*[1]', namespaces=doc.nsmap)[0]
        resp.status = str(auth_doc.xpath('local-name()'))
        if (resp.status == 'authenticationSuccess'):
            resp.authenticated = True
            resp.user = str(auth_doc.xpath('string(./cas:user)', namespaces=doc.nsmap))
            attributes = auth_doc.xpath('./cas:attributes/*', namespaces=doc.nsmap)
            for attribute in attributes:
                resp.attributes[str(attribute.xpath('local-name()'))] = str(attribute.text)
        else:
            resp.authenticated = False
        return resp

    def _parse_profile(self, raw):
        data = json.loads(raw)
        resp = CasResponse(authenticated=True, user=data['id'])
        for attribute in data['attributes'].keys():
            resp.attributes[attribute] = data['attributes'][attribute]
        return resp

def get_client():
    return CasClient(settings.CAS_SERVER_URL)

def get_login_url(*args, **kwargs):
    """Convenience function for getting a login URL for a service.

    :param args: Same args that `CasClient.get_login_url` receives
    :param kwargs: Same kwargs that `CasClient.get_login_url` receives
    """
    return get_client().get_login_url(*args, **kwargs)

def make_response_from_ticket(ticket, service_url):
    """Given a CAS ticket and service URL, attempt to the user and return a proper
    redirect response.
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
        return authenticate(user, response=redirect(service_furl.url), access_token=cas_resp.attributes['accessToken'])
    # Ticket could not be validated, unauthorized.
    return redirect(service_furl.url)
