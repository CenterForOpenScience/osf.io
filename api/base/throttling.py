from rest_framework.settings import api_settings as drf_settings
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle, SimpleRateThrottle

from api.base import settings


class BaseThrottle(SimpleRateThrottle):

    def failure(self, request):
        return False

    def get_ident(self, request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        remote_addr = request.META.get('REMOTE_ADDR')
        throttle_token = request.META.get('HTTP_X_THROTTLE_TOKEN')
        num_proxies = drf_settings.NUM_PROXIES

        if throttle_token:
            return throttle_token

        if num_proxies is not None:
            if num_proxies == 0 or xff is None:
                return remote_addr
            addrs = xff.split(',')
            client_addr = addrs[-min(num_proxies, len(addrs))]
            return client_addr.strip()

        return ''.join(xff.split()) if xff else remote_addr

    def allow_request(self, request, view):
        """
        Implement the check to see if the request should be throttled.
        """
        throttle_token = settings.BYPASS_THROTTLE_TOKEN
        if throttle_token and self.get_ident(request) == throttle_token:
            return True

        if self.rate is None:
            return True

        self.key = self.get_cache_key(request, view)
        if self.key is None:
            return True

        self.history = self.cache.get(self.key, [])
        self.now = self.timer()

        # Drop any requests from the history which have now passed the throttle duration
        while self.history and self.history[-1] <= self.now - self.duration:
            self.history.pop()

        if len(self.history) >= self.num_requests:
            return self.failure(request)
        return self.throttle_success()


class NonCookieAuthThrottle(BaseThrottle, AnonRateThrottle):

    scope = 'non-cookie-auth'

    def failure(self, request):
        return bool(request.COOKIES)


class AddContributorThrottle(BaseThrottle, UserRateThrottle):

    scope = 'add-contributor'

    def failure(self, request):
        if request.method == 'POST' and request.query_params.get('send_email') != 'false':
            return False
        return True


class CreateGuidThrottle(BaseThrottle, UserRateThrottle):

    scope = 'create-guid'

    def failure(self, request):
        if request.query_params.get('create_guid'):
            return False
        return True


class RootAnonThrottle(AnonRateThrottle):

    scope = 'root-anon-throttle'


class TestUserRateThrottle(BaseThrottle, UserRateThrottle):

    scope = 'test-user'


class TestAnonRateThrottle(BaseThrottle, AnonRateThrottle):

    scope = 'test-anon'
