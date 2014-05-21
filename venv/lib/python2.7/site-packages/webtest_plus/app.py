# -*- coding: utf-8 -*-
from base64 import b64encode

import webtest
from webtest import utils

from webtest_plus.response import TestResponse
from webtest_plus.compat import PY2, binary_type


def _basic_auth_str(username, password):
    """Returns a Basic Auth string."""
    return 'Basic ' + b64encode(('%s:%s' % (username, password)).encode('latin1')).strip().decode('latin1')


def _add_auth(auth, headers):
    '''Adds authentication key to headers.'''
    headers = headers or {}
    if isinstance(auth, (tuple, list)) and len(auth) == 2:
        if PY2:
            auth_header = binary_type(_basic_auth_str(*auth))
        else:
            auth_header = _basic_auth_str(*auth)
        headers["Authorization"] = auth_header
    return headers


class TestRequest(webtest.app.TestRequest):
    ResponseClass = TestResponse


class TestApp(webtest.TestApp):
    '''A modified webtest.TestApp with useful features such as
    requests-style authentication and auto_follow.

    Example: ::

        >>> from my_wsgi_app import application
        >>> from webtest_plus import TestApp
        >>> app = TestApp(application)
        >>> app.get("/protected/", auth=("admin", "passw0rd"))
        >>> app.status_code
        200
    '''
    RequestClass = TestRequest

    def __init__(self, app, *args, **kwargs):
        super(TestApp, self).__init__(app, *args, **kwargs)
        self.auth = None

    def _build_headers(self, headers, auth):
        auth_tuple = auth or self.auth
        if auth_tuple:
            headers = _add_auth(auth_tuple, headers)
        return headers

    def authenticate(self, username, password):
        '''Store HTTP basic authentication information for future requests.'''
        self.auth = (username, password)

    def deauthenticate(self):
        '''Remove authentication information.'''
        self.auth = None

    def get(self, url, params=None, headers=None, extra_environ=None,
            status=None, expect_errors=False, xhr=False, auth=None,
            auto_follow=False, **kwargs):
        response = super(TestApp, self).get(
                        url, params, headers=self._build_headers(headers, auth),
                        extra_environ=extra_environ, status=status,
                        expect_errors=expect_errors, xhr=xhr)
        is_redirect = lambda r: r.status_int >= 300 and r.status_int < 400
        while auto_follow and is_redirect(response):
            response = response.follow()
        return response

    def post(self, url, params='', headers=None, extra_environ=None,
             status=None, upload_files=None, expect_errors=False,
             content_type=None, xhr=False, auth=None, **kwargs):
        return super(TestApp, self).post(
                    url, params, headers=self._build_headers(headers, auth),
                    extra_environ=extra_environ, status=status,
                    upload_files=upload_files, expect_errors=expect_errors,
                    content_type=content_type, xhr=xhr, **kwargs)

    def put(self, url, params='', headers=None, extra_environ=None,
            status=None, upload_files=None, expect_errors=False,
            content_type=None, xhr=False, auth=None, **kwargs):
        return super(TestApp, self).put(
                    url, params, headers=self._build_headers(headers, auth),
                    extra_environ=extra_environ, status=status,
                    upload_files=upload_files, expect_errors=expect_errors,
                    content_type=content_type, xhr=xhr, **kwargs)

    def patch(self, url, params='', headers=None, extra_environ=None,
              status=None, upload_files=None, expect_errors=False,
              content_type=None, xhr=False, auth=None, **kwargs):
        return super(TestApp, self).patch(
                    url, params, headers=self._build_headers(headers, auth),
                    extra_environ=extra_environ, status=status,
                    upload_files=upload_files, expect_errors=expect_errors,
                    content_type=content_type, xhr=xhr, **kwargs)

    def options(self, url, headers=None, extra_environ=None,
                status=None, expect_errors=False, xhr=False, auth=None, **kwargs):
        return super(TestApp, self).options(
                    url=url,
                    headers=self._build_headers(headers, auth),
                    extra_environ=extra_environ,
                    status=status,
                    expect_errors=expect_errors, xhr=xhr, **kwargs)

    def delete(self, url, params=utils.NoDefault, headers=None,
               extra_environ=None, status=None, expect_errors=False,
               content_type=None, xhr=False, auth=None, **kwargs):
        return super(TestApp, self).delete(
                        url=url, params=params,
                        headers=self._build_headers(headers, auth),
                        extra_environ=extra_environ,
                        status=status,
                        expect_errors=expect_errors,
                        content_type=content_type, xhr=xhr, **kwargs)

    def _gen_request(self, method, url, params=utils.NoDefault,
                     headers=None, extra_environ=None, status=None,
                     upload_files=None, expect_errors=False,
                     content_type=None, auth=None, **kwargs):
        """Do a generic request.
        """
        return super(TestApp, self)._gen_request(method=method,
                                                url=url,
                                                params=params,
                                                headers=self._build_headers(headers, auth),
                                                extra_environ=extra_environ,
                                                status=status,
                                                upload_files=upload_files,
                                                expect_errors=expect_errors,
                                                content_type=content_type,
                                                **kwargs)

    post_json = utils.json_method('POST')
    put_json = utils.json_method('PUT')
    patch_json = utils.json_method('PATCH')
    delete_json = utils.json_method('DELETE')
