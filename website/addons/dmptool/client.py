__all__ = ['DMPTool']

import requests

DMPTOOL_HOST = 'dmptool.org'
STAGING_DMPTOOL_HOST = 'dmp2-staging.cdlib.org'


def _connect(host, token):
    return DMPTool(token, host)

def connect_from_settings(node_settings):
    if not (node_settings and node_settings.external_account):
        return None

    host = node_settings.external_account.oauth_key
    token = node_settings.external_account.oauth_secret

    try:
        return _connect(host, token)
    except Exception:
        return None


def connect_or_error(host, token):

    # TO DO -- actually do a check on validity of token if possible
    # https://github.com/CDLUC3/dmptool/issues/183

    # in the mean time return a DMPTool

    # need to change DMPTool to account for host
    return DMPTool(token, host)


def connect_from_settings_or_401(node_settings):
    if not (node_settings and node_settings.external_account):
        return None

    host = node_settings.external_account.oauth_key
    token = node_settings.external_account.oauth_secret

    return connect_or_error(host, token)


class DMPTool(object):
    """
    TO DO: completely eliminate DMPTool since I don't think 
    there should be any remaining API code (other than perhaps
    validate a token.  The main action has moved to WB.)
    """
    def __init__(self, token, host='dmptool.org', protocol='https'):
        self.token = token
        self.host = host
        self.base_url = '{}://{}/api/v1/'.format(protocol, host)
        self.headers = {'Authorization': 'Token token={}'.format(self.token)}

    # def get_url(self, path, headers=None):
    #     if headers is None:
    #         headers = self.headers

    #     url = self.base_url + path
    #     response = requests.get(url, headers=headers)

    #     response.raise_for_status()
    #     return response

    # def _unroll(self, plans):
    #     """
    #     each plan is a dict with a key plan
    #     """
    #     return [
    #         plan.get('plan')
    #         for plan in plans
    #     ]

    # def plans(self, id_=None):
    #     """
    #     https://dmptool.org/api/v1/plans
    #     https://dmptool.org/api/v1/plans/:id
    #     """

    #     if id_ is None:
    #         return self._unroll(self.get_url('plans').json())
    #     else:
    #         return self.get_url('plans/{}'.format(id_)).json().get('plan')

    # def plans_full(self, id_=None, format_='json'):

    #     if id_ is None:
    #         # a json doc for to represent all public docs
    #         # I **think** if we include token, will get only docs owned
    #         return self._unroll(self.get_url('plans_full/', headers={}).json())
    #     else:
    #         if format_ == 'json':
    #             return self.get_url('plans_full/{}'.format(id_)).json().get('plan')
    #         elif format_ in ['pdf', 'docx']:
    #             return self.get_url('plans_full/{}.{}'.format(id_, format_)).content
    #         else:
    #             return None

    # def plans_owned(self, visibility_filter=('test',)):
    #     """
    #     by default, filter out plans that have 'test' for visibility
    #     (leaving public, private, institutional )
    #     https://github.com/CDLUC3/dmptool/issues/206
    #     """
    #     plans = self._unroll(self.get_url('plans_owned').json())
    #     return [plan for plan in plans if plan['visibility'] not in visibility_filter]

    # def plans_owned_full(self):
    #     return self._unroll(self.get_url('plans_owned_full').json())

    # def plans_templates(self):
    #     return self._unroll(self.get_url('plans_templates').json())

    # def institutions_plans_count(self):
    #     """
    #     https://github.com/CDLUC3/dmptool/wiki/API#for-a-list-of-institutions-and-plans-count
    #     """
    #     plans_counts = self.get_url('institutions_plans_count').json()
    #     return plans_counts
