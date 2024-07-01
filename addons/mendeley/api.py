from mendeley.session import MendeleySession


class APISession(MendeleySession):

    def request(self, *args, **kwargs):
        kwargs['params'] = {'view': 'all', 'limit': '500'}
        return super().request(*args, **kwargs)
