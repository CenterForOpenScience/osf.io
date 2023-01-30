import requests
from website import settings

from osf.external.askismet.exceptions import AkismetClientError


class AkismetClient(object):

    NAME = 'akismet'
    API_PROTOCOL = 'https://'
    API_HOST = 'rest.akismet.com'
    apikey = settings.AKISMET_APIKEY
    website = settings.DOMAIN

    @property
    def _default_headers(self):
        return {
            'content-type': 'application/x-www-form-urlencoded'
        }

    def check_content(self, user_ip, user_agent, **kwargs):
        """
        Check if a comment is spam

        :param: str user_ip:
        :param: str user_agent:

        :return: a (bool, str) tuple representing (is_spam, pro_tip)
        """
        allowed_args = (
            'referrer',
            'permalink',
            'is_test',
            'comment_author',
            'comment_author_email',
            'comment_author_url',
            'comment_content',
            'comment_date_gmt',
            'comment_post_modified_gmt'
        )

        allowed_kwargs = {
            k: kwargs.get(k)
            for k in allowed_args
            if k in kwargs
        }

        data = {
            'blog': self.website,
            'user_ip': user_ip,
            'user_agent': user_agent
        }
        data.update(allowed_kwargs)

        res = requests.post(
            f'{self.API_PROTOCOL}{self.apikey}.{self.API_HOST}/1.1/comment-check',
            data=data,
            headers=self._default_headers,
            timeout=5
        )

        if res.status_code != requests.codes.ok:
            raise AkismetClientError(reason=res.text)

        return res.text == 'true', res.headers.get('X-akismet-pro-tip')

    def submit_spam(self, user_ip, user_agent, **kwargs):
        allowed_args = (
            'referrer',
            'permalink',
            'is_test',
            'comment_author',
            'comment_author_email',
            'comment_author_url',
            'comment_content'
        )
        allowed_kwargs = {
            k: kwargs.get(k)
            for k in allowed_args
            if k in kwargs
        }
        data = {
            'blog': self.website,
            'user_ip': user_ip,
            'user_agent': user_agent,
        }
        data.update(allowed_kwargs)

        res = requests.post(
            f'{self.API_PROTOCOL}{self.apikey}.{self.API_HOST}/1.1/submit-spam',
            data=data,
            headers=self._default_headers
        )
        if res.status_code != requests.codes.ok:
            raise AkismetClientError(reason=res.text)

    def submit_ham(self, user_ip, user_agent, **kwargs):
        allowed_args = (
            'referrer',
            'permalink',
            'is_test',
            'comment_author',
            'comment_author_email',
            'comment_author_url',
            'comment_content'
        )
        allowed_kwargs = {
            k: kwargs.get(k)
            for k in allowed_args
            if k in kwargs
        }
        data = {
            'blog': self.website,
            'user_ip': user_ip,
            'user_agent': user_agent,
        }
        data.update(allowed_kwargs)

        res = requests.post(
            f'{self.API_PROTOCOL}{self.apikey}.{self.API_HOST}/1.1/submit-ham',
            data=data,
            headers=self._default_headers
        )
        if res.status_code != requests.codes.ok:
            raise AkismetClientError(reason=res.text)
