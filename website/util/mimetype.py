import os
import mimetypes

HERE = os.path.dirname(os.path.abspath(__file__))
MIMEMAP = os.path.join(HERE, 'mime.types')


def get_mimetype(path, file_contents=None):
    mimetypes.init([MIMEMAP])
    mimetype, _ = mimetypes.guess_type(path)

    if mimetype is None:
        try:
            import magic
            if file_contents is not None:
                mimetype = magic.from_buffer(file_contents, mime=True)
            else:
                mimetype = magic.from_file(path, mime=True)
        except ImportError:
            return mimetype

    return mimetype
