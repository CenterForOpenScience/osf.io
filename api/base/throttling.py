from rest_framework.throttling import UserRateThrottle, AnonRateThrottle, SimpleRateThrottle


class BaseThrottle(SimpleRateThrottle):

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
            return self.throttle_failure()
        return self.throttle_success()


class NonCookieAuthThrottle(BaseThrottle, AnonRateThrottle):

    scope = 'non-cookie-auth'

    def allow_request(self, request, view):
        """
        Allow all unauthenticated requests that are made with a cookie.
        """
        if bool(request.COOKIES):
            return True

        return super(NonCookieAuthThrottle, self).allow_request(request, view)


class AddContributorThrottle(BaseThrottle, UserRateThrottle):

    scope = 'add-contributor'

    def allow_request(self, request, view):
        """
        Allow all add contributor requests that do not send contributor emails.
        """
        if request.method == 'POST' and request.query_params.get('send_email') == 'false':
            return True

        return super(AddContributorThrottle, self).allow_request(request, view)


class CreateGuidThrottle(BaseThrottle, UserRateThrottle):

    scope = 'create-guid'

    def allow_request(self, request, view):
        """
        Allow all create file requests that do not create new guids.
        """
        if not request.query_params.get('create_guid'):
            return True

        return super(CreateGuidThrottle, self).allow_request(request, view)


class RootAnonThrottle(AnonRateThrottle):

    scope = 'root-anon-throttle'


class TestUserRateThrottle(UserRateThrottle):

    scope = 'test-user'


class TestAnonRateThrottle(AnonRateThrottle):

    scope = 'test-anon'
