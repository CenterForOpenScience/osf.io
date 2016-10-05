import requests

from requests.exceptions import RequestException


class AkismetClientError(Exception):

    def __init__(self, reason):
        super(AkismetClientError, self).__init__(reason)
        self.reason = reason


class AkismetClient(object):

    API_PROTOCOL = 'https://'
    API_HOST = 'rest.akismet.com'

    def __init__(self, apikey, website, verify=False):
        self.apikey = apikey
        self.website = website
        self._apikey_is_valid = None
        if verify:
            self._verify_apikey()

    @property
    def _default_headers(self):
        return {
            'content-type': 'application/x-www-form-urlencoded'
        }

    def _is_apikey_valid(self):
        if self._apikey_is_valid is not None:
            return self._apikey_is_valid
        else:
            res = requests.post(
                '{}{}/1.1/verify-key'.format(self.API_PROTOCOL, self.API_HOST),
                data={
                    'key': self.apikey,
                    'blog': self.website
                },
                headers=self._default_headers
            )
            self._apikey_is_valid = (res.text == 'valid')
            return self._is_apikey_valid()

    def _verify_apikey(self):
        if not self._is_apikey_valid():
            raise AkismetClientError('Invalid API key')

    def check_comment(self, user_ip, user_agent, **kwargs):
        """
        Check if a comment is spam

        :param: str user_ip:
        :param: str user_agent:

        :return: a (bool, str) tuple representing (is_spam, pro_tip)
        """
        ALLOWED_ARGS = ('referrer', 'permalink', 'is_test',
                        'comment_author', 'comment_author_email', 'comment_author_url',
                        'comment_content', 'comment_date_gmt', 'comment_post_modified_gmt')
        data = {
            k: kwargs.get(k)
            for k in ALLOWED_ARGS
            if k in kwargs
        }
        data['blog'] = self.website
        data['user_ip'] = user_ip
        data['user_agent'] = user_agent

        try:
            res = requests.post(
                '{}{}.{}/1.1/comment-check'.format(self.API_PROTOCOL, self.apikey, self.API_HOST),
                data=data,
                headers=self._default_headers,
                timeout=5
            )
            res.raise_for_status()
        except RequestException as e:
            raise AkismetClientError(reason=e.args[0])
        return res.text == 'true', res.headers.get('X-akismet-pro-tip')

    def submit_spam(self, user_ip, user_agent, **kwargs):
        ALLOWED_ARGS = ('referrer', 'permalink', 'is_test',
                        'comment_author', 'comment_author_email', 'comment_author_url', 'comment_content')
        data = {
            k: kwargs.get(k)
            for k in ALLOWED_ARGS
            if k in kwargs
        }
        data['blog'] = self.website
        data['user_ip'] = user_ip
        data['user_agent'] = user_agent

        res = requests.post(
            '{}{}.{}/1.1/submit-spam'.format(self.API_PROTOCOL, self.apikey, self.API_HOST),
            data=data,
            headers=self._default_headers
        )
        if res.status_code != requests.codes.ok:
            raise AkismetClientError(reason=res.text)

    def submit_ham(self, user_ip, user_agent, **kwargs):
        ALLOWED_ARGS = ('referrer', 'permalink', 'is_test',
                        'comment_author', 'comment_author_email', 'comment_author_url', 'comment_content')
        data = {
            k: kwargs.get(k)
            for k in ALLOWED_ARGS
            if k in kwargs
        }
        data['blog'] = self.website
        data['user_ip'] = user_ip
        data['user_agent'] = user_agent

        res = requests.post(
            '{}{}.{}/1.1/submit-ham'.format(self.API_PROTOCOL, self.apikey, self.API_HOST),
            data=data,
            headers=self._default_headers
        )
        if res.status_code != requests.codes.ok:
            raise AkismetClientError(reason=res.text)
