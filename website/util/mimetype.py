import os
import mimetypes


def get_mimetype(path, data=None):
    HERE = os.path.dirname(os.path.abspath(__file__))
    MIMEMAP = os.path.join(HERE, 'mime.types')
    mimetypes.init([MIMEMAP])
    mimetype, _ = mimetypes.guess_type(path)

    if mimetype is None:
        try:
            import magic
            mimetype = magic.from_buffer(data, mime=True)
        except ImportError:
            return mimetype

    return mimetype