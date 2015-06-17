from ghostpy import Compiler
from ghostpy._compiler import _ghostpy_

class Renderer:

    def __init__(self, theme):
        self.theme = theme
        self.compiler = Compiler(theme)


    def _asset(self, *args, **kwargs):
        if args[1] == 'favicon.ico':
            return "/static/ghost_themes/public/favicon.ico"
        return self.theme[7:] + "/assets/" + args[1]


    def _ghost_foot(self, *args, **kwargs):
        return "<script type='text/javascript' src='/static/ghost_themes/public/jquery.js'></script>"


    def _navigation(self, *args, **kwards):
        path = self.theme + '/partials/navigation.hbs'
        output = self.render(path)
        return output

 
    def render(self, file, dict_=None):
        blog_dict = {
            'url': 'url.com',
            'title': 'Test Title',
            'description': 'Test description',
            'navigation': [{
                'label': 'Test',
                'url': 'test.com',
                'current': True,
                'slug': 'Test'
            }, {
                'label': 'Test2',
                'url': 'test2.com',
                'current': False,
                'slug': 'Test2'
            }, {
                'label': 'Test3',
                'url': 'test3.com',
                'current': False,
                'slug': 'Test3'
            }]
        }
        with open(file) as hbs:
            source = hbs.read().decode('unicode-escape')
        if dict_ is not None:
            _dict = dict(dict_, **blog_dict)
        else: _dict = blog_dict
        _ghostpy_['blog_dict'] = _dict
        template = self.compiler.compile(source)
        output = template(_dict, {"asset": self._asset, "ghost_foot": self._ghost_foot, "navigation": self._navigation})
        return output
