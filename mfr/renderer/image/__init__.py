from .. import FileRenderer
import os.path
import imghdr


class ImageRenderer(FileRenderer):

    def _detect(self, file_pointer):
        """Detects whether a given file pointer can be rendered by
        this renderer. Checks both the extension in list and the file encoding
        using the imghdr lib

        :param file_pointer: File pointer
        :return: Can file be rendered? (bool)

        """
        _, ext = os.path.splitext(file_pointer.name)
        if ext.lower() in ['.jpeg', '.jpg', '.png', '.bmp', '.gif']:
            if imghdr.what(file_pointer):
                return True
        return False

    def _render(self, file_pointer, **kwargs):
        url = kwargs['url']
        return "<img src='{0}'/>".format(url)
