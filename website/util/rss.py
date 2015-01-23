# Sublclass for PyRSS2Gen and PubSubHubbub headers
from PyRSS2Gen import RSS2, _element


class RSS2_Pshb(RSS2):

    def publish_extensions(self, handler):
        _element(handler, 'link', self.link, {'rel': 'self', 'href': self.link})
        _element(handler, 'link', 'https://pubsubhubbub.appspot.com/', {'rel': 'hub', 'href': 'https://pubsubhubbub.appspot.com/'})
