import furl
import json
import requests

from lxml import etree


class CasResponse(object):

    authenticated = False
    status = None
    user = None
    attributes = {}


class CasClient(object):

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
        url = furl.furl(self.BASE_URL)
        url.path.segments.extend(('p3', 'serviceValidate',))
        url.args['ticket'] = ticket
        url.args['service'] = service_url

        resp = requests.get(url.url)
        if resp.status_code == 200:
            return self._parse_service_validation(resp.content)
        else:
            return CasResponse()

    def profile(self, access_token):
        url = furl.furl(self.BASE_URL)
        url.path.segments.extend(('oauth2', 'profile',))
        headers = {
            'Authorization': 'Bearer {}'.format(access_token),
        }
        resp = requests.get(url.url, headers=headers)
        if resp.status_code == 200:
            return self._parse_profile(resp.content)
        else:
            return CasResponse()

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
        resp = CasResponse()
        data = json.loads(raw)
        resp.authenticated = True
        resp.user = data['id']
        for attribute in data['attributes'].keys():
            resp.attributes[attribute] = data['attributes'][attribute]
        return resp
