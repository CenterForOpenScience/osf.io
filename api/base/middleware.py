import re
import gc
import uuid
import json
from io import StringIO
from urllib.parse import urlparse
import cProfile
import pstats
import threading

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from raven.contrib.django.raven_compat.models import sentry_exception_handler
import corsheaders.middleware

from framework.postcommit_tasks.handlers import (
    postcommit_after_request,
    postcommit_before_request,
)
from framework.celery_tasks.handlers import (
    celery_before_request,
    celery_after_request,
    celery_teardown_request,
)
from .api_globals import api_globals
from api.base import settings as api_settings
from waffle.middleware import WaffleMiddleware
from waffle.models import Flag

from website.settings import DOMAIN
from osf.models import (
    Preprint,
    PreprintProvider,
)
from typing import Optional

from osf.features import (
    SLOAN_COI_DISPLAY,
    SLOAN_PREREG_DISPLAY,
    SLOAN_DATA_DISPLAY,
)

from osf.system_tags import (
    SLOAN_COI,
    SLOAN_PREREG,
    SLOAN_DATA,
)

SLOAN_FLAGS = (
    SLOAN_COI_DISPLAY,
    SLOAN_PREREG_DISPLAY,
    SLOAN_DATA_DISPLAY,
)

# User tags must follow convention so we must translate flag names
SLOAN_FEATURES = {
    SLOAN_COI_DISPLAY: SLOAN_COI,
    SLOAN_PREREG_DISPLAY: SLOAN_PREREG,
    SLOAN_DATA_DISPLAY: SLOAN_DATA,

}

from django.db.models import Q


class CeleryTaskMiddleware(MiddlewareMixin):
    """Celery Task middleware."""

    def process_request(self, request):
        celery_before_request()

    def process_exception(self, request, exception):
        """If an exception occurs, clear the celery task queue so process_response has nothing."""
        sentry_exception_handler(request=request)
        celery_teardown_request(error=True)
        return None

    def process_response(self, request, response):
        """Clear the celery task queue if the response status code is 400 or above"""
        celery_after_request(response, base_status_code_error=400)
        celery_teardown_request()
        return response


class DjangoGlobalMiddleware(MiddlewareMixin):
    """
    Store request object on a thread-local variable for use in database caching mechanism.
    """
    def process_request(self, request):
        api_globals.request = request

    def process_exception(self, request, exception):
        sentry_exception_handler(request=request)
        api_globals.request = None
        return None

    def process_response(self, request, response):
        api_globals.request = None
        if api_settings.DEBUG and len(gc.get_referents(request)) > 2:
            raise Exception('You wrote a memory leak. Stop it')
        return response


class CorsMiddleware(corsheaders.middleware.CorsMiddleware):
    """
    Augment CORS origin white list with the Institution model's domains.
    """

    _context = threading.local()

    def origin_found_in_white_lists(self, origin, url):
        settings.CORS_ORIGIN_WHITELIST += api_settings.ORIGINS_WHITELIST
        # Check if origin is in the dynamic custom domain whitelist
        found = super(CorsMiddleware, self).origin_found_in_white_lists(origin, url)
        # Check if a cross-origin request using the Authorization header
        if not found:
            if not self._context.request.COOKIES:
                if self._context.request.META.get('HTTP_AUTHORIZATION'):
                    return True
                elif (
                    self._context.request.method == 'OPTIONS' and
                    'HTTP_ACCESS_CONTROL_REQUEST_METHOD' in self._context.request.META and
                    'authorization' in list(map(
                        lambda h: h.strip(),
                        self._context.request.META.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS', '').split(','),
                    ))
                ):
                    return True

        return found

    def process_response(self, request, response):
        self._context.request = request
        try:
            return super(CorsMiddleware, self).process_response(request, response)
        finally:
            self._context.request = None


class PostcommitTaskMiddleware(MiddlewareMixin):
    """
    Handle postcommit tasks for django.
    """
    def process_request(self, request):
        postcommit_before_request()

    def process_response(self, request, response):
        postcommit_after_request(response=response, base_status_error_code=400)
        return response


# Adapted from http://www.djangosnippets.org/snippets/186/
# Original author: udfalkso
# Modified by: Shwagroo Team and Gun.io
# Modified by: COS
class ProfileMiddleware(MiddlewareMixin):
    """
    Displays hotshot profiling for any view.
    http://yoursite.com/yourview/?prof
    Add the "prof" key to query string by appending ?prof (or &prof=)
    and you'll see the profiling results in your browser.
    It's set up to only be available in django's debug mode, is available for superuser otherwise,
    but you really shouldn't add this middleware to any production configuration.
    """
    def process_request(self, request):
        if (settings.DEBUG or request.user.is_superuser) and 'prof' in request.GET:
            self.prof = cProfile.Profile()

    def process_view(self, request, callback, callback_args, callback_kwargs):
        if (settings.DEBUG or request.user.is_superuser) and 'prof' in request.GET:
            self.prof.enable()

    def process_response(self, request, response):
        if (settings.DEBUG or request.user.is_superuser) and 'prof' in request.GET:
            self.prof.disable()

            s = StringIO.StringIO()
            ps = pstats.Stats(self.prof, stream=s).sort_stats('cumtime')
            ps.print_stats()
            response.content = s.getvalue()

        return response


class SloanOverrideWaffleMiddleware(WaffleMiddleware):
    """
    This class exist to override Waffles normal cookie behavior, so sloan cookies are cross-domain and have no
    expiration date. It can be deleted when the Sloan study is complete/
    """

    def process_response(self, request, response):
        waffles = getattr(request, 'waffles', None)
        if request.path == '/v2/' and not getattr(response, 'accepted_media_type', None) == 'text/html':  # exclude browserable api
            content_data = json.loads(response.content.decode())

            # clear flags initially
            if content_data['meta'].get('active_flags'):
                content_data['meta']['active_flags'] = [flag for flag in content_data['meta']['active_flags'] if flag not in SLOAN_FLAGS]

            user = getattr(request, 'user', None)
            referer_url = request.environ.get('HTTP_REFERER', '')
            provider = self.get_provider_from_url(referer_url)

            if provider and provider.in_sloan_study:
                for sloan_flag_name in SLOAN_FLAGS:
                    active = self.override_flag_activity(sloan_flag_name, waffles, user)

                    if active is not None:
                        self.set_sloan_tags(user, sloan_flag_name, active)
                        self.set_sloan_cookie(
                            f'dwf_{sloan_flag_name}',
                            active,
                            request.environ['HTTP_REFERER'],
                            request,
                            response,
                        )

                        if provider.domain_redirect_enabled and provider.domain:
                            self.set_sloan_cookie(
                                f'dwf_{sloan_flag_name}_custom_domain',
                                active,
                                request.environ['HTTP_REFERER'],
                                request,
                                response,
                                custom_domain=provider.domain,
                            )

                            if not request.COOKIES.get(settings.SLOAN_ID_COOKIE_NAME):
                                self.set_sloan_cookie(
                                    settings.SLOAN_ID_COOKIE_NAME,
                                    str(uuid.uuid4()),
                                    request.environ['HTTP_REFERER'],
                                    request,
                                    response,
                                    custom_domain=provider.domain,
                                )

                        if active:
                            content_data['meta']['active_flags'].append(sloan_flag_name)

            elif user and not user.is_anonymous:
                for sloan_flag_name in SLOAN_FLAGS:
                    tag = SLOAN_FEATURES[sloan_flag_name]
                    if user.all_tags.filter(name=tag).exists():
                        content_data['meta']['active_flags'].append(sloan_flag_name)
                        self.set_sloan_cookie(
                            f'dwf_{sloan_flag_name}',
                            True,
                            request.environ['SERVER_NAME'],
                            request,
                            response,
                        )

                    elif user.all_tags.filter(name=f'no_{tag}').exists():
                        self.set_sloan_cookie(
                            f'dwf_{sloan_flag_name}',
                            False,
                            request.environ['SERVER_NAME'],
                            request,
                            response,
                        )

            response.content = json.dumps(content_data).encode()

        # `set_sloan_cookies` has set the cookies, make sure WaffleMiddleware doesn't try to set them again.
        if waffles:
            for sloan_flag_name in SLOAN_FLAGS:
                if waffles.get(sloan_flag_name):
                    del waffles[sloan_flag_name]

        # Give all users a unique id 'sloan_id` cookie, logged in or not.
        if not request.COOKIES.get(settings.SLOAN_ID_COOKIE_NAME):
            self.set_sloan_cookie(
                settings.SLOAN_ID_COOKIE_NAME,
                str(uuid.uuid4()),
                request.environ['SERVER_NAME'] or request.environ.get('HTTP_REFERER'),
                request,
                response,
            )

        return super(SloanOverrideWaffleMiddleware, self).process_response(request, response)

    @staticmethod
    def get_domain(url: str) -> str:
        """
        http://localhost:8000/preprints -> localhost
        http://osf.io/preprints/... -> .osf.io
        http://im-a-custom-domain.io/... -> .osf.io
        http://staging-im-a-custom-domain.io/... -> .staging.osf.io


        :param url:
        :return:
        """
        if url.startswith('http://localhost:'):
            return 'localhost'
        else:
            # for custom domains
            if url.startswith('http://staging3') or url.startswith('https://staging3'):
                return '.staging3.osf.io'
            if url.startswith('http://staging2') or url.startswith('https://staging2'):
                return '.staging2.osf.io'
            if url.startswith('http://test') or url.startswith('https://test'):
                return '.test.osf.io'
            if url.startswith('http://staging') or url.startswith('https://staging'):
                return '.staging.osf.io'
            else:
                return '.osf.io'

    @staticmethod
    def get_provider_from_url(referer_url: str) -> Optional[PreprintProvider]:
        """
        Takes the many preprint refer urls and try to figure out the provider based on that.
        This will be eliminated post-sloan.
        :param referer_url:
        :return: PreprintProvider
        """

        # matches custom domains:
        provider_domains = list(
            PreprintProvider.objects.exclude(
                domain='',
            ).filter(
                domain_redirect_enabled=True,  # must exclude our native domains like https://staging2.osf.io/
            ).values_list(
                'domain',
                flat=True,
            ),
        )
        provider_domains = [domains for domains in provider_domains if referer_url.startswith(domains)]

        if provider_domains:
            return PreprintProvider.objects.get(domain=provider_domains[0])

        provider_ids_regex = '|'.join(
            [re.escape(id) for id in PreprintProvider.objects.all().values_list('_id', flat=True)],
        )
        # matches:
        # /ispp0  (preprint id)
        path = urlparse(referer_url).path.replace('/', '')
        preprint = Preprint.load(path)
        if preprint:
            return preprint.provider

        # matches:
        # /preprints
        # /preprints/
        # /preprints/notfound
        # /preprints/foorxiv
        # /preprints/foorxiv/
        # /preprints/foorxiv/guid0
        provider_regex = r'preprints($|\/$|\/(?P<provider_id>{})|)'.format(provider_ids_regex)
        match = re.match(re.escape(DOMAIN) + provider_regex, referer_url)
        if match:
            provider_id = match.groupdict().get('provider_id')
            if provider_id:
                return PreprintProvider.objects.get(_id=provider_id)
            return PreprintProvider.objects.get(_id='osf')

    @staticmethod
    def override_flag_activity(sloan_flag_name, waffles_data, user):
        active = None
        if waffles_data and waffles_data.get(sloan_flag_name):
            active = waffles_data[sloan_flag_name][0]

        if user and not user.is_anonymous:
            tag_name = SLOAN_FEATURES[sloan_flag_name]
            if user.all_tags.filter(name=tag_name).exists():
                active = True
            elif user.all_tags.filter(name=f'no_{tag_name}').exists():
                active = False

        if Flag.objects.get(name=sloan_flag_name).everyone:
            active = True

        return active

    @staticmethod
    def set_sloan_tags(user, flag_name: str, flag_value: bool):
        """
        This sets user tags for Sloan study, it can be deleted when the study is complete.
        """
        tag_name = SLOAN_FEATURES[flag_name]
        if user and not user.is_anonymous and not user.all_tags.filter(Q(name=tag_name) | Q(name=f'no_{tag_name}')):
            if flag_value:  # 50/50 chance flag is active
                user.add_system_tag(tag_name)
            else:
                user.add_system_tag(f'no_{tag_name}')

    def set_sloan_cookie(self, name: str, value, url, request, resp, custom_domain=None):
        """
        Set sloan cookies to sloan study specifications
        :param name: The name of the flag that will get a cookie
        :param value: Is the flag active, what's it's value if sloan_id
        :param request:
        :param resp:
        :return:
        """
        resp.cookies[name] = value
        # ↓ This line seems terrible but is fixed in py 3.8
        resp.cookies[name]._reserved.update({'samesite': 'samesite'})

        resp.cookies[name]['path'] = '/'

        resp.cookies[name]['domain'] = self.get_domain(url)

        if custom_domain:
            resp.cookies[name]['domain'] = '.' + urlparse(custom_domain).netloc

        # Browsers won't allow use to use these cookie attributes unless you're sending the data over https.
        resp.cookies[name]['secure'] = True
        resp.cookies[name]['samesite'] = 'None'
