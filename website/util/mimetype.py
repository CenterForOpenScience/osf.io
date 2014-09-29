import os
import mimetypes

HERE = os.path.dirname(os.path.abspath(__file__))
MIMEMAP = os.path.join(HERE, 'mime.types')


def get_mimetype(path, file_contents=None):
    mimetypes.init([MIMEMAP])
    mimetype, _ = mimetypes.guess_type(path)

    if mimetype is None and file_contents is not None:
        try:
            import magic
            mimetype = magic.from_buffer(file_contents, mime=True)
        except ImportError:
            return mimetype

    return mimetype