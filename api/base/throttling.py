from rest_framework.throttling import UserRateThrottle, AnonRateThrottle, SimpleRateThrottle


class BaseThrottle(SimpleRateThrottle):

    def failure(self, request):
        return False

    def allow_request(self, request, view):
        """
        Implement the check to see if the request should be throttled.
        """
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


class TestUserRateThrottle(UserRateThrottle):

    scope = 'test-user'


class TestAnonRateThrottle(AnonRateThrottle):

    scope = 'test-anon'
