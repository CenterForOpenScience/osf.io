import mimetypes


def get_mimetype(path, data=None):
    mimetypes.init()
    mimetype, _ = mimetypes.guess_type(path)

    if mimetype is None:
        try:
            import magic
            mimetype = magic.from_buffer(data, mime=True)
        except ImportError:
            return mimetype

    return mimetype