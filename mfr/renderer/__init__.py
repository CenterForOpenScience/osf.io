import os
import inspect
from hurry.filesize import size
from mako.lookup import TemplateLookup


class FileMeta(type):

    def __init__(cls, name, bases, dct):
        
        # Call super-metaclass __init__
        super(FileMeta, cls).__init__(name, bases, dct)
        
        # Initialize class registry and add self
        if not hasattr(cls, 'registry'):
            cls.registry = {}
        if name != 'FileRenderer':
            cls.registry[name] = cls

        class_file = inspect.getfile(cls)
        cls.path = os.path.split(class_file)[0]
        cls.mako_lookup = TemplateLookup(
            directories=[os.path.join(cls.path, 'templates')]
        )
        

# class RenderError(Exception):
#todo add later for specific renderer error handling -ajs
#     def __init__(self, *args, **kwargs):
#         super(RenderError, self).__init__(*args, **kwargs)
#         self.details = kwargs['details']
#
#     def to_html(self):
#         return self.base + self.details


class FileRenderer(object):

    __metaclass__ = FileMeta

    STATIC_PATH = '/static/mfr/'
    MAX_SIZE = 1024*1024*2.5

    @classmethod
    def _render_mako(cls, filename, **kwargs):
        return cls.mako_lookup.get_template(filename).render(**kwargs)
    
    def _check_size(self, file_pointer):
        return os.stat(file_pointer.name).st_size > self.MAX_SIZE

    def render(self, file_pointer, **kwargs):

        if self._check_size(file_pointer):
            return '''<div>
                This file is too large to be displayed in your browser. To view this file,
                download it and open it offline.
            </div>'''

        _, file_name = os.path.split(file_pointer.name)
        # try:
        rendered = self._render(file_pointer, **kwargs)
        # except RenderError as error:
        #     rendered = error.to_html()
        # except Exception as error:
        #     logger.error(error)
        # rendered = 'Unable to render; download file to view it'
        return rendered

    def _detect(self, file_pointer):
        """Detects whether a given file pointer can be rendered by 
        this renderer. Each renderer needs a detect method that at minimum
        checks the file extension, but ideally includes other checks (e.g.,
        mimetype, file encodings, etc).

        :param file_pointer: File pointer
        :return: Can file be rendered? (bool)

        """
        return False

    def _render(self, file_pointer, **kwargs):
        """Renders a file to HTML.

        :param file_pointer: File pointer
        :return: HTML rendition of file

        """
        return ""
