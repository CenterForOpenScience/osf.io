__all__ = ['DMPTool']

import requests
import urlparse

class DMPTool(object):
    def __init__(self, token, prod=True):
        self.token = token
        self.prod = prod
        if prod:
            self.base_url = "https://dmptool.org/api/v1/"
        else:
            self.base_url = "https://dmp2-staging.cdlib.org/api/v1/"
        self.headers = {'Authorization': 'Token token={}'.format(self.token)}
                
    def get_url(self, path, headers=None):
        if headers is None:
            headers = self.headers
            
        url = self.base_url + path
        return requests.get(url, headers=headers)
    
    def plans(self, id_=None):
        """
        https://dmptool.org/api/v1/plans
        https://dmptool.org/api/v1/plans/:id
        """
        
        if id_ is None:
            return self.get_url("plans").json()
        else:
            return self.get_url("plans/{}".format(id_)).json()
                    
    def plans_full(self, id_=None, format_='json'):
    
        if id_ is None:
            # a json doc for to represent all public docs
            # I **think** if we include token, will get only docs owned
            return self.get_url("plans_full/", headers={}).json()
        else:
            if format_ == 'json':
                return self.get_url("plans_full/{}".format(id_)).json()
            elif format_ in ['pdf', 'docx']:
                return self.get_url("plans_full/{}.{}".format(id_, format_)).content
            else: 
                return None

    def plans_owned(self):
        return self.get_url("plans_owned").json()
    
    def plans_owned_full(self):
        return self.get_url("plans_owned_full").json()
    
    def plans_templates(self):
        return self.get_url("plans_templates").json()
        
    def institutions_plans_count(self):
        """
        https://github.com/CDLUC3/dmptool/wiki/API#for-a-list-of-institutions-and-plans-count
        """
        plans_counts = self.get_url("institutions_plans_count").json()
        return plans_counts

    
