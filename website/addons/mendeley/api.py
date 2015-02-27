from mendeley.session import MendeleySession


class APISession(MendeleySession):

    def request(self, *args, **kwargs):
        kwargs['params'] = {'view': 'all'}
        return super(APISession, self).request(*args, **kwargs)