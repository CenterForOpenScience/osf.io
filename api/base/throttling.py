from rest_framework.throttling import UserRateThrottle, AnonRateThrottle, SimpleRateThrottle


class CookieAuthThrottle(AnonRateThrottle):

    rate = '100/hour'

    def allow_request(self, request, view):
        return bool(request.COOKIES)

    def wait(self):
        return 3600


class AddContributorThrottle(UserRateThrottle):

    rate = '10/second'

    def allow_request(self, request, view):
        if request.method == 'POST' and request.query_params.get('send_email') != 'false':
            return False
        return True

    def wait(self):
        return 0.1


class TestUserThrottle(UserRateThrottle):

    rate = '2/hour'


class TestAnonRateThrottle(AnonRateThrottle):

    rate = '1/hour'
