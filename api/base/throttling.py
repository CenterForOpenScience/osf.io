from rest_framework.throttling import UserRateThrottle


class AddContributorThrottle(UserRateThrottle):

    def allow_request(self, request, view):
        return request.method == 'POST' and request.query_params.get('send_email') is not False

    def wait(self):
        return 0.1
