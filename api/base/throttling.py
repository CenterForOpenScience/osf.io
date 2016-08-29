from rest_framework.throttling import UserRateThrottle, AnonRateThrottle, SimpleRateThrottle


class BaseThrottle(SimpleRateThrottle):

    def success(self):
        self.history.insert(0, self.now)
        self.cache.set(self.key, self.history, self.duration)
        return True

    def failure(self, request):
        return False

    def allow_request(self, request, view):
        """
        Implement the check to see if the request should be throttled.
        On success calls `throttle_success`.
        On failure calls `throttle_failure`.
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
        return self.success()


class CookieAuthThrottle(AnonRateThrottle, BaseThrottle):

    rate = '100/hour'

    def failure(self, request):
        return bool(request.COOKIES)

    def wait(self):
        return 3600


class AddContributorThrottle(UserRateThrottle, BaseThrottle):

    rate = '10/second'

    def failure(self, request):
        if request.method == 'POST' and request.query_params.get('send_email') != 'false':
            return False
        return True

    def wait(self):
        return 0.1


class TestUserThrottle(UserRateThrottle):

    rate = '2/hour'


class TestAnonRateThrottle(AnonRateThrottle):

    rate = '1/hour'
