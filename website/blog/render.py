from ghostpy import Compiler
from ghostpy._compiler import _ghostpy_
# from compiler import Compiler
# from compiler import _ghostpy_

class Renderer:

    def __init__(self, theme):
        self.theme = theme
        self.compiler = Compiler(theme)


    def _asset(self, *args, **kwargs):
        if args[2] == 'favicon.ico':
            return "/static/ghost_themes/public/favicon.ico"
        return self.theme[7:] + "/assets/" + args[2]


    def _ghost_foot(self, *args, **kwargs):
        return "<script type='text/javascript' src='/static/ghost_themes/public/jquery.js'></script>"


    def render(self, file, blog_dict, dict_=None):
        with open(file) as hbs:
            source = hbs.read().decode('unicode-escape')
        if dict_ is not None:
            _dict = dict(dict_, **blog_dict)
        else: _dict = blog_dict
        _ghostpy_['blog_dict'] = _dict
        template = self.compiler.compile(source)
        output = template(_dict, {"asset": self._asset, "ghost_foot": self._ghost_foot})
        return output
