from .. import FileRenderer
import os

class AudioRenderer(FileRenderer):

    def __init__(self, max_width=None):
        self.max_width = max_width

    def _detect(self, file_pointer):
        _, ext = os.path.splitext(file_pointer.name)
        return ext.lower() in ['.wav', '.mp3']

    def _render(self, file_pointer, **kwargs):
        url = kwargs['url']
        return '<audio controls><source src="{file_path}">'.format(file_path=url, file_name=file_pointer.name)
