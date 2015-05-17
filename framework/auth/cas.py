import furl
import requests

from lxml import etree


class CasResponse:

    def __init__(self):
        self._authenticated = False
        self._status = None
        self._user = None
        self._attributes = {}

    @property
    def authenticated(self):
        return self._authenticated

    @authenticated.setter
    def authenticated(self, value):
        self._authenticated = value

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, value):
        self._user = value

    @property
    def attributes(self):
        return self._attributes


class CasClient:

    def __init__(self, base_url):
        self.BASE_URL = base_url

    def get_login_url(self, service_url, auto=False):
        url = furl.furl(self.BASE_URL)
        url.path.segments.append('login')
        url.args['service'] = service_url
        if auto:
            url.args['auto'] = 'true'
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
